-- ISOLATED CANDIDATE ONLY. No live migration.
BEGIN;
CREATE ROLE mixer_hosted_schema_owner NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION;
CREATE ROLE mixer_hosted_authz_resolver NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION;
CREATE ROLE mixer_hosted_domain_writer NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION;
CREATE ROLE mixer_hosted_runtime LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION;
REVOKE ALL ON DATABASE authority_contract FROM PUBLIC;
GRANT CONNECT ON DATABASE authority_contract TO mixer_hosted_runtime;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
CREATE SCHEMA mixer_authz AUTHORIZATION mixer_hosted_schema_owner;
REVOKE ALL ON SCHEMA mixer_authz FROM PUBLIC;
GRANT USAGE ON SCHEMA mixer_authz TO mixer_hosted_authz_resolver,mixer_hosted_domain_writer,mixer_hosted_runtime;
SET ROLE mixer_hosted_schema_owner;
ALTER DEFAULT PRIVILEGES REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
ALTER DEFAULT PRIVILEGES REVOKE USAGE ON TYPES FROM PUBLIC;
CREATE FUNCTION mixer_authz.finite_uint(n numeric,lo numeric,hi numeric) RETURNS boolean LANGUAGE sql IMMUTABLE PARALLEL UNSAFE SET search_path=pg_catalog AS $$ SELECT coalesce(n IS NOT NULL AND n::text NOT IN ('NaN','Infinity','-Infinity') AND n BETWEEN lo AND hi AND trunc(n)=n,false) $$;
CREATE FUNCTION mixer_authz.bounded_text(t text,hi integer) RETURNS boolean LANGUAGE sql IMMUTABLE PARALLEL UNSAFE SET search_path=pg_catalog AS $$ SELECT coalesce(octet_length(t) BETWEEN 1 AND hi,false) $$;
CREATE FUNCTION mixer_authz.valid_id(t text) RETURNS boolean LANGUAGE sql IMMUTABLE PARALLEL UNSAFE SET search_path=pg_catalog AS $$ SELECT coalesce(octet_length(t) BETWEEN 1 AND 128 AND t COLLATE "C" ~ '^[A-Za-z0-9_.-]+$',false) $$;
CREATE TYPE mixer_authz.verified_identity_v1 AS (profile_id text,profile_version integer,issuer text,subject text,client_id text,credential_sha256 bytea,issued_at numeric,expires_at numeric,identity_class text,scopes text[],authentication_completed_at numeric);
CREATE TYPE mixer_authz.target_v1 AS (action text,organization text,project text,app text,environment text,platform text,runtime_sha256 bytea,manifest_sha256 bytea);
CREATE TYPE mixer_authz.transaction_identity_v1 AS (backend integer,full_xid text,database_name name,runtime_role name,nonce text,deadline timestamptz);
CREATE TYPE mixer_authz.admission_v1 AS (identity mixer_authz.verified_identity_v1,target mixer_authz.target_v1,transaction_identity mixer_authz.transaction_identity_v1,principal_id uuid,binding_id uuid,family_id uuid,profile_revision bigint,principal_revision bigint,family_revision bigint,organization_revision bigint,project_revision bigint,lock_statement_at timestamptz);
CREATE TYPE mixer_authz.membership_witness_v1 AS (lifecycle_id uuid,role text,revision bigint);
CREATE TYPE mixer_authz.decision_v1 AS (outcome text,principal_id uuid,binding_id uuid,family_id uuid,decision_at numeric,profile_revision bigint,principal_revision bigint,family_revision bigint,organization_revision bigint,project_revision bigint,memberships mixer_authz.membership_witness_v1[]);
CREATE TABLE mixer_authz.identity_trust_profiles(profile_id text COLLATE "C" PRIMARY KEY CHECK(mixer_authz.bounded_text(profile_id,128)),current_version integer NOT NULL CHECK(current_version>0),enabled boolean NOT NULL,issuer text COLLATE "C" NOT NULL CHECK(mixer_authz.bounded_text(issuer,2048)),client_id text COLLATE "C" NOT NULL CHECK(mixer_authz.bounded_text(client_id,256)),identity_class text NOT NULL CHECK(identity_class IN ('human','service')),revision bigint NOT NULL CHECK(revision>0),UNIQUE(profile_id,issuer,client_id,identity_class));
CREATE TABLE mixer_authz.organizations(organization text COLLATE "C" PRIMARY KEY CHECK(mixer_authz.valid_id(organization)),status text NOT NULL CHECK(status IN ('active','deleted')),revision bigint NOT NULL CHECK(revision>0));
CREATE TABLE mixer_authz.principals(principal_id uuid PRIMARY KEY,kind text NOT NULL CHECK(kind IN ('human','service')),status text NOT NULL CHECK(status IN ('active','disabled')),valid_after bigint NOT NULL CHECK(valid_after BETWEEN 0 AND 9007199254740991),revision bigint NOT NULL CHECK(revision>0),owning_organization text COLLATE "C" REFERENCES mixer_authz.organizations,CHECK((kind='human' AND owning_organization IS NULL) OR (kind='service' AND owning_organization IS NOT NULL)),UNIQUE(principal_id,kind));
CREATE TABLE mixer_authz.external_identity_bindings(binding_id uuid PRIMARY KEY,profile_id text COLLATE "C" NOT NULL,issuer text COLLATE "C" NOT NULL,subject text COLLATE "C" NOT NULL CHECK(mixer_authz.bounded_text(subject,256)),registered_client text COLLATE "C" NOT NULL,identity_class text NOT NULL,principal_id uuid NOT NULL,FOREIGN KEY(profile_id,issuer,registered_client,identity_class) REFERENCES mixer_authz.identity_trust_profiles(profile_id,issuer,client_id,identity_class),FOREIGN KEY(principal_id,identity_class) REFERENCES mixer_authz.principals(principal_id,kind),UNIQUE(profile_id,issuer,subject,registered_client),UNIQUE(binding_id,principal_id,profile_id));
CREATE TABLE mixer_authz.credential_families(family_id uuid PRIMARY KEY,binding_id uuid NOT NULL,principal_id uuid NOT NULL,profile_id text COLLATE "C" NOT NULL,status text NOT NULL CHECK(status IN ('active','revoked')),valid_after bigint NOT NULL CHECK(valid_after BETWEEN 0 AND 9007199254740991),revision bigint NOT NULL CHECK(revision>0),FOREIGN KEY(binding_id,principal_id,profile_id) REFERENCES mixer_authz.external_identity_bindings(binding_id,principal_id,profile_id),UNIQUE(family_id,binding_id,principal_id,profile_id));
CREATE TABLE mixer_authz.credential_references(binding_id uuid NOT NULL,jti_sha256 bytea NOT NULL CHECK(octet_length(jti_sha256)=32),family_id uuid NOT NULL,principal_id uuid NOT NULL,profile_id text COLLATE "C" NOT NULL,accepted_issued_at bigint NOT NULL CHECK(accepted_issued_at BETWEEN 0 AND 9007199254740991),accepted_expires_at bigint NOT NULL CHECK(accepted_expires_at BETWEEN 0 AND 9007199254740991),PRIMARY KEY(binding_id,jti_sha256),FOREIGN KEY(family_id,binding_id,principal_id,profile_id) REFERENCES mixer_authz.credential_families(family_id,binding_id,principal_id,profile_id),CHECK(accepted_issued_at<accepted_expires_at),UNIQUE(binding_id,jti_sha256,accepted_expires_at));
CREATE TABLE mixer_authz.credential_denials(binding_id uuid NOT NULL,jti_sha256 bytea NOT NULL,accepted_expires_at bigint NOT NULL,denied_at bigint NOT NULL CHECK(denied_at BETWEEN 0 AND 9007199254740991),retain_until bigint NOT NULL CHECK(retain_until BETWEEN 0 AND 9007199254741021),revision bigint NOT NULL CHECK(revision>0),reason_code text NOT NULL CHECK(reason_code IN ('revoked','incident','operator')),PRIMARY KEY(binding_id,jti_sha256),FOREIGN KEY(binding_id,jti_sha256,accepted_expires_at) REFERENCES mixer_authz.credential_references(binding_id,jti_sha256,accepted_expires_at),CHECK(retain_until>=accepted_expires_at+30));
CREATE TABLE mixer_authz.projects(organization text COLLATE "C" NOT NULL REFERENCES mixer_authz.organizations,project text COLLATE "C" NOT NULL CHECK(mixer_authz.valid_id(project)),status text NOT NULL CHECK(status IN ('active','deleted')),revision bigint NOT NULL CHECK(revision>0),PRIMARY KEY(organization,project));
CREATE TABLE mixer_authz.applications(organization text COLLATE "C" NOT NULL,project text COLLATE "C" NOT NULL,app text COLLATE "C" NOT NULL CHECK(mixer_authz.valid_id(app)),status text NOT NULL CHECK(status IN ('active','deleted')),revision bigint NOT NULL CHECK(revision>0),PRIMARY KEY(organization,project,app),FOREIGN KEY(organization,project) REFERENCES mixer_authz.projects);
CREATE TABLE mixer_authz.environments(organization text COLLATE "C" NOT NULL,project text COLLATE "C" NOT NULL,app text COLLATE "C" NOT NULL,environment text COLLATE "C" NOT NULL CHECK(mixer_authz.valid_id(environment)),status text NOT NULL CHECK(status IN ('active','deleted')),risk_class text NOT NULL CHECK(risk_class IN ('development','staging','production')),revision bigint NOT NULL CHECK(revision>0),PRIMARY KEY(organization,project,app,environment),FOREIGN KEY(organization,project,app) REFERENCES mixer_authz.applications);
CREATE TABLE mixer_authz.organization_authorization_heads(organization text COLLATE "C" PRIMARY KEY REFERENCES mixer_authz.organizations,revision bigint NOT NULL CHECK(revision>0));
CREATE TABLE mixer_authz.project_authorization_heads(organization text COLLATE "C" NOT NULL,project text COLLATE "C" NOT NULL,revision bigint NOT NULL CHECK(revision>0),PRIMARY KEY(organization,project),FOREIGN KEY(organization,project) REFERENCES mixer_authz.projects);

CREATE TABLE mixer_authz.organization_memberships(lifecycle_id uuid PRIMARY KEY,organization text COLLATE "C" NOT NULL REFERENCES mixer_authz.organizations,project_binding text NOT NULL CHECK(project_binding IN ('organization_wide','organization_only')),principal_id uuid NOT NULL REFERENCES mixer_authz.principals,role text NOT NULL CHECK(role IN ('owner','administrator','developer','release_manager','billing_manager','viewer')),status text NOT NULL CHECK(status IN ('invited','active','revoked')),not_before bigint CHECK(not_before BETWEEN 0 AND 9007199254740991),expires_at bigint CHECK(expires_at BETWEEN 0 AND 9007199254740991),revision bigint NOT NULL CHECK(revision>0),grant_evidence_sha256 bytea NOT NULL CHECK(octet_length(grant_evidence_sha256)=32),CHECK(not_before IS NULL OR expires_at IS NULL OR not_before<expires_at));
CREATE INDEX organization_memberships_lookup ON mixer_authz.organization_memberships(principal_id,organization,project_binding,status);
CREATE UNIQUE INDEX organization_memberships_active_unique ON mixer_authz.organization_memberships(principal_id,organization,project_binding,role) WHERE status='active';
CREATE TABLE mixer_authz.project_memberships(lifecycle_id uuid PRIMARY KEY,organization text COLLATE "C" NOT NULL,project text COLLATE "C" NOT NULL,principal_id uuid NOT NULL REFERENCES mixer_authz.principals,role text NOT NULL CHECK(role IN ('owner','administrator','developer','release_manager','billing_manager','viewer')),status text NOT NULL CHECK(status IN ('invited','active','revoked')),not_before bigint CHECK(not_before BETWEEN 0 AND 9007199254740991),expires_at bigint CHECK(expires_at BETWEEN 0 AND 9007199254740991),revision bigint NOT NULL CHECK(revision>0),grant_evidence_sha256 bytea NOT NULL CHECK(octet_length(grant_evidence_sha256)=32),CHECK(not_before IS NULL OR expires_at IS NULL OR not_before<expires_at),FOREIGN KEY(organization,project) REFERENCES mixer_authz.projects);
CREATE INDEX project_memberships_lookup ON mixer_authz.project_memberships(principal_id,organization,project,status);
CREATE UNIQUE INDEX project_memberships_active_unique ON mixer_authz.project_memberships(principal_id,organization,project,role) WHERE status='active';
CREATE INDEX credential_families_binding ON mixer_authz.credential_families(binding_id,principal_id,profile_id);
CREATE INDEX bindings_principal ON mixer_authz.external_identity_bindings(principal_id,profile_id);
ALTER TABLE mixer_authz.identity_trust_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE mixer_authz.identity_trust_profiles FORCE ROW LEVEL SECURITY;
GRANT SELECT ON mixer_authz.identity_trust_profiles TO mixer_hosted_authz_resolver;
CREATE POLICY resolver_select ON mixer_authz.identity_trust_profiles FOR SELECT TO mixer_hosted_authz_resolver USING(true);
ALTER TABLE mixer_authz.principals ENABLE ROW LEVEL SECURITY;
ALTER TABLE mixer_authz.principals FORCE ROW LEVEL SECURITY;
GRANT SELECT ON mixer_authz.principals TO mixer_hosted_authz_resolver;
CREATE POLICY resolver_select ON mixer_authz.principals FOR SELECT TO mixer_hosted_authz_resolver USING(true);
ALTER TABLE mixer_authz.external_identity_bindings ENABLE ROW LEVEL SECURITY;
ALTER TABLE mixer_authz.external_identity_bindings FORCE ROW LEVEL SECURITY;
GRANT SELECT ON mixer_authz.external_identity_bindings TO mixer_hosted_authz_resolver;
CREATE POLICY resolver_select ON mixer_authz.external_identity_bindings FOR SELECT TO mixer_hosted_authz_resolver USING(true);
ALTER TABLE mixer_authz.credential_families ENABLE ROW LEVEL SECURITY;
ALTER TABLE mixer_authz.credential_families FORCE ROW LEVEL SECURITY;
GRANT SELECT ON mixer_authz.credential_families TO mixer_hosted_authz_resolver;
CREATE POLICY resolver_select ON mixer_authz.credential_families FOR SELECT TO mixer_hosted_authz_resolver USING(true);
ALTER TABLE mixer_authz.credential_references ENABLE ROW LEVEL SECURITY;
ALTER TABLE mixer_authz.credential_references FORCE ROW LEVEL SECURITY;
GRANT SELECT ON mixer_authz.credential_references TO mixer_hosted_authz_resolver;
CREATE POLICY resolver_select ON mixer_authz.credential_references FOR SELECT TO mixer_hosted_authz_resolver USING(true);
ALTER TABLE mixer_authz.credential_denials ENABLE ROW LEVEL SECURITY;
ALTER TABLE mixer_authz.credential_denials FORCE ROW LEVEL SECURITY;
GRANT SELECT ON mixer_authz.credential_denials TO mixer_hosted_authz_resolver;
CREATE POLICY resolver_select ON mixer_authz.credential_denials FOR SELECT TO mixer_hosted_authz_resolver USING(true);
ALTER TABLE mixer_authz.organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE mixer_authz.organizations FORCE ROW LEVEL SECURITY;
GRANT SELECT ON mixer_authz.organizations TO mixer_hosted_authz_resolver;
CREATE POLICY resolver_select ON mixer_authz.organizations FOR SELECT TO mixer_hosted_authz_resolver USING(true);
ALTER TABLE mixer_authz.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE mixer_authz.projects FORCE ROW LEVEL SECURITY;
GRANT SELECT ON mixer_authz.projects TO mixer_hosted_authz_resolver;
CREATE POLICY resolver_select ON mixer_authz.projects FOR SELECT TO mixer_hosted_authz_resolver USING(true);
ALTER TABLE mixer_authz.applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE mixer_authz.applications FORCE ROW LEVEL SECURITY;
GRANT SELECT ON mixer_authz.applications TO mixer_hosted_authz_resolver;
CREATE POLICY resolver_select ON mixer_authz.applications FOR SELECT TO mixer_hosted_authz_resolver USING(true);
ALTER TABLE mixer_authz.environments ENABLE ROW LEVEL SECURITY;
ALTER TABLE mixer_authz.environments FORCE ROW LEVEL SECURITY;
GRANT SELECT ON mixer_authz.environments TO mixer_hosted_authz_resolver;
CREATE POLICY resolver_select ON mixer_authz.environments FOR SELECT TO mixer_hosted_authz_resolver USING(true);
ALTER TABLE mixer_authz.organization_authorization_heads ENABLE ROW LEVEL SECURITY;
ALTER TABLE mixer_authz.organization_authorization_heads FORCE ROW LEVEL SECURITY;
GRANT SELECT ON mixer_authz.organization_authorization_heads TO mixer_hosted_authz_resolver;
CREATE POLICY resolver_select ON mixer_authz.organization_authorization_heads FOR SELECT TO mixer_hosted_authz_resolver USING(true);
ALTER TABLE mixer_authz.project_authorization_heads ENABLE ROW LEVEL SECURITY;
ALTER TABLE mixer_authz.project_authorization_heads FORCE ROW LEVEL SECURITY;
GRANT SELECT ON mixer_authz.project_authorization_heads TO mixer_hosted_authz_resolver;
CREATE POLICY resolver_select ON mixer_authz.project_authorization_heads FOR SELECT TO mixer_hosted_authz_resolver USING(true);
ALTER TABLE mixer_authz.organization_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE mixer_authz.organization_memberships FORCE ROW LEVEL SECURITY;
GRANT SELECT ON mixer_authz.organization_memberships TO mixer_hosted_authz_resolver;
CREATE POLICY resolver_select ON mixer_authz.organization_memberships FOR SELECT TO mixer_hosted_authz_resolver USING(true);
ALTER TABLE mixer_authz.project_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE mixer_authz.project_memberships FORCE ROW LEVEL SECURITY;
GRANT SELECT ON mixer_authz.project_memberships TO mixer_hosted_authz_resolver;
CREATE POLICY resolver_select ON mixer_authz.project_memberships FOR SELECT TO mixer_hosted_authz_resolver USING(true);
GRANT UPDATE(revision) ON mixer_authz.identity_trust_profiles TO mixer_hosted_authz_resolver;
CREATE POLICY resolver_lock ON mixer_authz.identity_trust_profiles FOR UPDATE TO mixer_hosted_authz_resolver USING(true) WITH CHECK(true);
GRANT UPDATE(revision) ON mixer_authz.principals TO mixer_hosted_authz_resolver;
CREATE POLICY resolver_lock ON mixer_authz.principals FOR UPDATE TO mixer_hosted_authz_resolver USING(true) WITH CHECK(true);
GRANT UPDATE(revision) ON mixer_authz.credential_families TO mixer_hosted_authz_resolver;
CREATE POLICY resolver_lock ON mixer_authz.credential_families FOR UPDATE TO mixer_hosted_authz_resolver USING(true) WITH CHECK(true);
GRANT UPDATE(revision) ON mixer_authz.organization_authorization_heads TO mixer_hosted_authz_resolver;
CREATE POLICY resolver_lock ON mixer_authz.organization_authorization_heads FOR UPDATE TO mixer_hosted_authz_resolver USING(true) WITH CHECK(true);
GRANT UPDATE(revision) ON mixer_authz.project_authorization_heads TO mixer_hosted_authz_resolver;
CREATE POLICY resolver_lock ON mixer_authz.project_authorization_heads FOR UPDATE TO mixer_hosted_authz_resolver USING(true) WITH CHECK(true);
CREATE FUNCTION mixer_authz.guard_lifecycle() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'hard delete forbidden' USING ERRCODE='23514';END IF;
 IF TG_TABLE_NAME IN ('external_identity_bindings','credential_references') THEN RAISE EXCEPTION 'immutable binding' USING ERRCODE='23514';END IF;
 IF (to_jsonb(NEW)->>'revision')::bigint<>(to_jsonb(OLD)->>'revision')::bigint+1 THEN RAISE EXCEPTION 'revision must increment exactly' USING ERRCODE='23514';END IF;
 IF TG_TABLE_NAME='identity_trust_profiles' THEN
  IF ROW(NEW.profile_id,NEW.issuer,NEW.client_id,NEW.identity_class) IS DISTINCT FROM ROW(OLD.profile_id,OLD.issuer,OLD.client_id,OLD.identity_class) OR NEW.current_version<OLD.current_version OR (NOT OLD.enabled AND NEW.enabled AND NEW.current_version<=OLD.current_version) THEN RAISE EXCEPTION 'profile identity/version immutable' USING ERRCODE='23514';END IF;
 ELSIF TG_TABLE_NAME='principals' THEN
  IF ROW(NEW.principal_id,NEW.kind,NEW.owning_organization) IS DISTINCT FROM ROW(OLD.principal_id,OLD.kind,OLD.owning_organization) OR NEW.valid_after<OLD.valid_after THEN RAISE EXCEPTION 'principal immutable/cutoff' USING ERRCODE='23514';END IF;
 ELSIF TG_TABLE_NAME='credential_families' THEN
  IF ROW(NEW.family_id,NEW.binding_id,NEW.principal_id,NEW.profile_id) IS DISTINCT FROM ROW(OLD.family_id,OLD.binding_id,OLD.principal_id,OLD.profile_id) OR NEW.valid_after<OLD.valid_after OR (OLD.status='revoked' AND NEW.status<>'revoked') THEN RAISE EXCEPTION 'family immutable/cutoff' USING ERRCODE='23514';END IF;
 ELSIF TG_TABLE_NAME='organization_memberships' OR TG_TABLE_NAME='project_memberships' THEN
  IF (to_jsonb(NEW)-ARRAY['status','not_before','expires_at','revision']) IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['status','not_before','expires_at','revision']) OR (OLD.status='revoked' AND NEW.status<>'revoked') THEN RAISE EXCEPTION 'membership lifecycle immutable' USING ERRCODE='23514';END IF;
 ELSE
  IF (to_jsonb(NEW)-ARRAY['status','risk_class','revision']) IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['status','risk_class','revision']) OR (to_jsonb(OLD)->>'status'='deleted' AND to_jsonb(NEW)->>'status'<>'deleted') THEN RAISE EXCEPTION 'resource identity immutable' USING ERRCODE='23514';END IF;
 END IF;RETURN NEW;
END $$;
CREATE TRIGGER lifecycle_guard BEFORE UPDATE OR DELETE ON mixer_authz.identity_trust_profiles FOR EACH ROW EXECUTE FUNCTION mixer_authz.guard_lifecycle();
CREATE TRIGGER lifecycle_guard BEFORE UPDATE OR DELETE ON mixer_authz.principals FOR EACH ROW EXECUTE FUNCTION mixer_authz.guard_lifecycle();
CREATE TRIGGER lifecycle_guard BEFORE UPDATE OR DELETE ON mixer_authz.external_identity_bindings FOR EACH ROW EXECUTE FUNCTION mixer_authz.guard_lifecycle();
CREATE TRIGGER lifecycle_guard BEFORE UPDATE OR DELETE ON mixer_authz.credential_families FOR EACH ROW EXECUTE FUNCTION mixer_authz.guard_lifecycle();
CREATE TRIGGER lifecycle_guard BEFORE UPDATE OR DELETE ON mixer_authz.credential_references FOR EACH ROW EXECUTE FUNCTION mixer_authz.guard_lifecycle();
CREATE TRIGGER lifecycle_guard BEFORE UPDATE OR DELETE ON mixer_authz.credential_denials FOR EACH ROW EXECUTE FUNCTION mixer_authz.guard_lifecycle();
CREATE TRIGGER lifecycle_guard BEFORE UPDATE OR DELETE ON mixer_authz.organizations FOR EACH ROW EXECUTE FUNCTION mixer_authz.guard_lifecycle();
CREATE TRIGGER lifecycle_guard BEFORE UPDATE OR DELETE ON mixer_authz.projects FOR EACH ROW EXECUTE FUNCTION mixer_authz.guard_lifecycle();
CREATE TRIGGER lifecycle_guard BEFORE UPDATE OR DELETE ON mixer_authz.applications FOR EACH ROW EXECUTE FUNCTION mixer_authz.guard_lifecycle();
CREATE TRIGGER lifecycle_guard BEFORE UPDATE OR DELETE ON mixer_authz.environments FOR EACH ROW EXECUTE FUNCTION mixer_authz.guard_lifecycle();
CREATE TRIGGER lifecycle_guard BEFORE UPDATE OR DELETE ON mixer_authz.organization_authorization_heads FOR EACH ROW EXECUTE FUNCTION mixer_authz.guard_lifecycle();
CREATE TRIGGER lifecycle_guard BEFORE UPDATE OR DELETE ON mixer_authz.project_authorization_heads FOR EACH ROW EXECUTE FUNCTION mixer_authz.guard_lifecycle();
CREATE TRIGGER lifecycle_guard BEFORE UPDATE OR DELETE ON mixer_authz.organization_memberships FOR EACH ROW EXECUTE FUNCTION mixer_authz.guard_lifecycle();
CREATE TRIGGER lifecycle_guard BEFORE UPDATE OR DELETE ON mixer_authz.project_memberships FOR EACH ROW EXECUTE FUNCTION mixer_authz.guard_lifecycle();
CREATE FUNCTION mixer_authz.validate_inputs(i mixer_authz.verified_identity_v1,t mixer_authz.target_v1) RETURNS void LANGUAGE plpgsql IMMUTABLE PARALLEL UNSAFE SET search_path=pg_catalog AS $$
DECLARE sc text;
BEGIN
 IF NOT mixer_authz.bounded_text(i.profile_id,128) OR i.profile_version IS NULL OR i.profile_version<1 OR NOT mixer_authz.bounded_text(i.issuer,2048) OR NOT mixer_authz.bounded_text(i.subject,256) OR NOT mixer_authz.bounded_text(i.client_id,256) OR i.credential_sha256 IS NULL OR octet_length(i.credential_sha256)<>32 OR i.identity_class IS DISTINCT FROM 'human' OR NOT mixer_authz.finite_uint(i.issued_at,0,9007199254740991) OR NOT mixer_authz.finite_uint(i.expires_at,0,9007199254740991) OR NOT mixer_authz.finite_uint(i.authentication_completed_at,0,9007199254740991) OR i.issued_at>=i.expires_at OR i.authentication_completed_at>=i.expires_at OR i.scopes IS NULL OR cardinality(i.scopes)>3 OR array_ndims(i.scopes)>1 OR (cardinality(i.scopes)>0 AND array_lower(i.scopes,1)<>1) THEN RAISE EXCEPTION 'invalid identity' USING ERRCODE='42501';END IF;
 FOREACH sc IN ARRAY i.scopes LOOP IF sc IS NULL OR sc NOT IN ('mixer.artifact.read','mixer.artifact.upload','mixer.audit.read') THEN RAISE EXCEPTION 'invalid scopes' USING ERRCODE='42501';END IF;END LOOP;
 IF (SELECT count(DISTINCT x) FROM unnest(i.scopes) x)<>cardinality(i.scopes) THEN RAISE EXCEPTION 'duplicate scopes' USING ERRCODE='42501';END IF;
 IF t.action IS NULL OR t.action NOT IN ('artifact.read','artifact.upload','audit.read') OR NOT mixer_authz.valid_id(t.organization) OR NOT mixer_authz.valid_id(t.project) THEN RAISE EXCEPTION 'invalid action/tenant' USING ERRCODE='42501';END IF;
 IF t.action='audit.read' THEN
  IF t.app IS NOT NULL OR t.environment IS NOT NULL OR t.platform IS NOT NULL OR t.runtime_sha256 IS NOT NULL OR t.manifest_sha256 IS NOT NULL THEN RAISE EXCEPTION 'invalid audit target' USING ERRCODE='42501';END IF;
 ELSIF NOT mixer_authz.valid_id(t.app) OR NOT mixer_authz.valid_id(t.environment) OR t.platform IS NULL OR t.platform NOT IN ('ios','android') OR t.runtime_sha256 IS NULL OR octet_length(t.runtime_sha256)<>32 OR t.manifest_sha256 IS NULL OR octet_length(t.manifest_sha256)<>32 THEN RAISE EXCEPTION 'invalid artifact target' USING ERRCODE='42501';END IF;
END $$;
CREATE FUNCTION mixer_authz.assert_transaction(x mixer_authz.transaction_identity_v1) RETURNS void LANGUAGE plpgsql VOLATILE PARALLEL UNSAFE SET search_path=pg_catalog AS $$
BEGIN
 IF session_user<>'mixer_hosted_runtime' OR current_setting('role')<>'none' OR current_setting('transaction_isolation')<>'read committed' OR x.backend IS DISTINCT FROM pg_backend_pid() OR x.full_xid IS DISTINCT FROM pg_current_xact_id()::text OR x.database_name IS DISTINCT FROM current_database()::name OR x.runtime_role IS DISTINCT FROM session_user::name OR x.nonce IS NULL OR x.nonce !~ '^[0-9a-f]{64}$' OR x.nonce IS DISTINCT FROM nullif(current_setting('mixer_authz.invocation_nonce',true),'') OR x.deadline IS NULL OR NOT isfinite(x.deadline) OR x.deadline<=clock_timestamp() OR x.deadline>clock_timestamp()+interval '5 seconds' OR x.deadline::text IS DISTINCT FROM nullif(current_setting('mixer_authz.deadline',true),'') THEN RAISE EXCEPTION 'transaction context rejected' USING ERRCODE='42501';END IF;
END $$;
CREATE FUNCTION mixer_authz.lookup_admission(i mixer_authz.verified_identity_v1,t mixer_authz.target_v1,x mixer_authz.transaction_identity_v1) RETURNS mixer_authz.admission_v1 LANGUAGE plpgsql VOLATILE SECURITY DEFINER PARALLEL UNSAFE SET search_path=pg_catalog SET row_security=on AS $$
DECLARE a mixer_authz.admission_v1;
BEGIN
 PERFORM mixer_authz.assert_transaction(x);PERFORM mixer_authz.validate_inputs(i,t);
 SELECT b.principal_id,b.binding_id,c.family_id INTO a.principal_id,a.binding_id,a.family_id FROM mixer_authz.external_identity_bindings b JOIN mixer_authz.credential_references c ON (c.binding_id,c.principal_id,c.profile_id)=(b.binding_id,b.principal_id,b.profile_id) WHERE b.profile_id=i.profile_id AND b.issuer=i.issuer AND b.subject=i.subject AND b.registered_client=i.client_id AND b.identity_class=i.identity_class AND c.jti_sha256=i.credential_sha256 AND c.accepted_issued_at=i.issued_at AND c.accepted_expires_at=i.expires_at;
 IF NOT FOUND THEN RAISE EXCEPTION 'credential rejected' USING ERRCODE='42501';END IF;
 a.identity:=i;a.target:=t;a.transaction_identity:=x;RETURN a;
END $$;
CREATE FUNCTION mixer_authz.lock_admission_rows(i mixer_authz.verified_identity_v1,t mixer_authz.target_v1,a mixer_authz.admission_v1,x mixer_authz.transaction_identity_v1) RETURNS mixer_authz.admission_v1 LANGUAGE plpgsql VOLATILE SECURITY DEFINER PARALLEL UNSAFE SET search_path=pg_catalog SET row_security=on AS $$
DECLARE b mixer_authz.admission_v1;r mixer_authz.admission_v1:=a;
BEGIN
 b:=mixer_authz.lookup_admission(i,t,x);
 IF a.identity IS DISTINCT FROM i OR a.target IS DISTINCT FROM t OR a.transaction_identity IS DISTINCT FROM x OR ROW(a.principal_id,a.binding_id,a.family_id) IS DISTINCT FROM ROW(b.principal_id,b.binding_id,b.family_id) THEN RAISE EXCEPTION 'admission substitution' USING ERRCODE='42501';END IF;
 SELECT p.revision INTO r.profile_revision FROM mixer_authz.identity_trust_profiles p WHERE p.profile_id=i.profile_id FOR SHARE;IF NOT FOUND THEN RAISE EXCEPTION 'lock row missing' USING ERRCODE='42501';END IF;
 SELECT p.revision INTO r.principal_revision FROM mixer_authz.principals p WHERE p.principal_id=a.principal_id FOR SHARE;IF NOT FOUND THEN RAISE EXCEPTION 'lock row missing' USING ERRCODE='42501';END IF;
 SELECT f.revision INTO r.family_revision FROM mixer_authz.credential_families f WHERE f.family_id=a.family_id AND f.binding_id=a.binding_id AND f.principal_id=a.principal_id AND f.profile_id=i.profile_id FOR SHARE;IF NOT FOUND THEN RAISE EXCEPTION 'lock row missing' USING ERRCODE='42501';END IF;
 SELECT h.revision INTO r.organization_revision FROM mixer_authz.organization_authorization_heads h WHERE h.organization=t.organization FOR SHARE;IF NOT FOUND THEN RAISE EXCEPTION 'lock row missing' USING ERRCODE='42501';END IF;
 SELECT h.revision INTO r.project_revision FROM mixer_authz.project_authorization_heads h WHERE (h.organization,h.project)=(t.organization,t.project) FOR SHARE;IF NOT FOUND THEN RAISE EXCEPTION 'lock row missing' USING ERRCODE='42501';END IF;
 -- Reassert immutable lookup after all locks. No capability is returned.
 b:=mixer_authz.lookup_admission(i,t,x);
 IF ROW(a.principal_id,a.binding_id,a.family_id) IS DISTINCT FROM ROW(b.principal_id,b.binding_id,b.family_id) THEN RAISE EXCEPTION 'mapping changed' USING ERRCODE='42501';END IF;
 r.lock_statement_at:=statement_timestamp();RETURN r;
END $$;
CREATE FUNCTION mixer_authz.recheck_current(i mixer_authz.verified_identity_v1,t mixer_authz.target_v1,a mixer_authz.admission_v1,x mixer_authz.transaction_identity_v1) RETURNS mixer_authz.decision_v1 LANGUAGE plpgsql VOLATILE SECURITY DEFINER PARALLEL UNSAFE SET search_path=pg_catalog SET row_security=on AS $$
DECLARE locked mixer_authz.admission_v1;d mixer_authz.decision_v1;p mixer_authz.identity_trust_profiles;pr mixer_authz.principals;f mixer_authz.credential_families;now_s numeric;members mixer_authz.membership_witness_v1[];eligible boolean;visible boolean;needed text;
BEGIN
 IF a.lock_statement_at IS NULL OR NOT isfinite(a.lock_statement_at) OR a.lock_statement_at>=statement_timestamp() THEN RAISE EXCEPTION 'separate lock statement required' USING ERRCODE='42501';END IF;
 -- Writer recheck NEVER acquires a lock: caller already holds canonical locks.
 locked:=mixer_authz.lookup_admission(i,t,x);
 IF a.identity IS DISTINCT FROM i OR a.target IS DISTINCT FROM t OR a.transaction_identity IS DISTINCT FROM x OR ROW(a.principal_id,a.binding_id,a.family_id) IS DISTINCT FROM ROW(locked.principal_id,locked.binding_id,locked.family_id) THEN RAISE EXCEPTION 'admission substitution' USING ERRCODE='42501';END IF;
 SELECT pp.revision,qq.revision,ff.revision,oh.revision,ph.revision INTO locked.profile_revision,locked.principal_revision,locked.family_revision,locked.organization_revision,locked.project_revision FROM mixer_authz.identity_trust_profiles pp CROSS JOIN mixer_authz.principals qq CROSS JOIN mixer_authz.credential_families ff CROSS JOIN mixer_authz.organization_authorization_heads oh CROSS JOIN mixer_authz.project_authorization_heads ph WHERE pp.profile_id=i.profile_id AND qq.principal_id=a.principal_id AND ff.family_id=a.family_id AND oh.organization=t.organization AND (ph.organization,ph.project)=(t.organization,t.project);
 IF NOT FOUND OR ROW(a.profile_revision,a.principal_revision,a.family_revision,a.organization_revision,a.project_revision) IS DISTINCT FROM ROW(locked.profile_revision,locked.principal_revision,locked.family_revision,locked.organization_revision,locked.project_revision) THEN RAISE EXCEPTION 'revision substitution/change' USING ERRCODE='42501';END IF;
 PERFORM mixer_authz.assert_transaction(x);
 -- This VOLATILE internal statement obtains fresh READ COMMITTED current state.
 SELECT pp.* INTO STRICT p FROM mixer_authz.identity_trust_profiles pp WHERE pp.profile_id=i.profile_id;
 SELECT qq.* INTO STRICT pr FROM mixer_authz.principals qq WHERE qq.principal_id=a.principal_id;
 SELECT ff.* INTO STRICT f FROM mixer_authz.credential_families ff WHERE ff.family_id=a.family_id;
 now_s:=floor(extract(epoch FROM clock_timestamp()));
 IF NOT mixer_authz.finite_uint(now_s,0,9007199254740991) OR NOT p.enabled OR p.current_version<>i.profile_version OR ROW(p.issuer,p.client_id,p.identity_class) IS DISTINCT FROM ROW(i.issuer,i.client_id,i.identity_class) OR pr.kind<>'human' OR pr.status<>'active' OR f.status<>'active' OR i.issued_at<pr.valid_after OR i.issued_at<f.valid_after OR now_s>=i.expires_at OR i.authentication_completed_at<now_s-45 OR i.authentication_completed_at>now_s+30 OR EXISTS(SELECT 1 FROM mixer_authz.credential_denials den WHERE den.binding_id=a.binding_id AND den.jti_sha256=i.credential_sha256) THEN RAISE EXCEPTION 'current credential rejected' USING ERRCODE='42501';END IF;
 d.principal_id:=a.principal_id;d.binding_id:=a.binding_id;d.family_id:=a.family_id;d.decision_at:=now_s;d.profile_revision:=locked.profile_revision;d.principal_revision:=locked.principal_revision;d.family_revision:=locked.family_revision;d.organization_revision:=locked.organization_revision;d.project_revision:=locked.project_revision;d.memberships:=ARRAY[]::mixer_authz.membership_witness_v1[];
 IF NOT EXISTS(SELECT 1 FROM mixer_authz.organizations o JOIN mixer_authz.projects pj USING(organization) WHERE o.organization=t.organization AND pj.project=t.project AND o.status='active' AND pj.status='active') OR (t.action<>'audit.read' AND NOT EXISTS(SELECT 1 FROM mixer_authz.applications ap JOIN mixer_authz.environments en USING(organization,project,app) WHERE (ap.organization,ap.project,ap.app,en.environment)=(t.organization,t.project,t.app,t.environment) AND ap.status='active' AND en.status='active')) THEN d.outcome:='not_found';RETURN d;END IF;
 SELECT array_agg(ROW(m.lifecycle_id,m.role,m.revision)::mixer_authz.membership_witness_v1 ORDER BY m.lifecycle_id) INTO members FROM (SELECT allm.* FROM (SELECT om.lifecycle_id,om.role,om.revision FROM mixer_authz.organization_memberships om WHERE om.principal_id=a.principal_id AND om.organization=t.organization AND om.project_binding='organization_wide' AND om.status='active' AND (om.not_before IS NULL OR om.not_before<=now_s) AND (om.expires_at IS NULL OR now_s<om.expires_at) UNION ALL SELECT pm.lifecycle_id,pm.role,pm.revision FROM mixer_authz.project_memberships pm WHERE pm.principal_id=a.principal_id AND (pm.organization,pm.project)=(t.organization,t.project) AND pm.status='active' AND (pm.not_before IS NULL OR pm.not_before<=now_s) AND (pm.expires_at IS NULL OR now_s<pm.expires_at)) allm ORDER BY allm.lifecycle_id LIMIT 65) m;
 IF cardinality(members)>64 OR (SELECT count(DISTINCT m.lifecycle_id) FROM unnest(members) m)<>coalesce(cardinality(members),0) THEN d.outcome:='authorization_unavailable';RETURN d;END IF;
 visible:=coalesce(cardinality(members)>0,false);IF NOT visible THEN d.outcome:='not_found';RETURN d;END IF;
 d.memberships:=members;
 SELECT bool_or(m.role IN ('owner','administrator','developer') OR (t.action<>'artifact.upload' AND m.role IN ('release_manager','viewer'))) INTO eligible FROM unnest(members) m;
 needed:=CASE t.action WHEN 'artifact.read' THEN 'mixer.artifact.read' WHEN 'artifact.upload' THEN 'mixer.artifact.upload' WHEN 'audit.read' THEN 'mixer.audit.read' END;
 d.outcome:=CASE WHEN eligible AND needed=ANY(i.scopes) THEN 'allowed' ELSE 'forbidden' END;
 IF floor(extract(epoch FROM clock_timestamp()))<>now_s THEN RAISE EXCEPTION 'decision clock advanced; retry fresh' USING ERRCODE='42501';END IF;
 PERFORM mixer_authz.assert_transaction(x);RETURN d;
END $$;

CREATE FUNCTION mixer_authz.decide_current(i mixer_authz.verified_identity_v1,t mixer_authz.target_v1,a mixer_authz.admission_v1,x mixer_authz.transaction_identity_v1) RETURNS mixer_authz.decision_v1 LANGUAGE plpgsql VOLATILE SECURITY DEFINER PARALLEL UNSAFE SET search_path=pg_catalog SET row_security=on AS $$
DECLARE locked mixer_authz.admission_v1;
BEGIN
 IF a.lock_statement_at IS NULL OR NOT isfinite(a.lock_statement_at) OR a.lock_statement_at>=statement_timestamp() THEN RAISE EXCEPTION 'separate lock statement required' USING ERRCODE='42501';END IF;
 -- Admission proves actual cardinality by acquiring every lock again. No tenant head yet.
 locked:=mixer_authz.lock_admission_rows(i,t,a,x);
 IF ROW(a.profile_revision,a.principal_revision,a.family_revision,a.organization_revision,a.project_revision) IS DISTINCT FROM ROW(locked.profile_revision,locked.principal_revision,locked.family_revision,locked.organization_revision,locked.project_revision) THEN RAISE EXCEPTION 'revision substitution/change' USING ERRCODE='42501';END IF;
 RETURN mixer_authz.recheck_current(i,t,a,x);
END $$;

RESET ROLE;
ALTER FUNCTION mixer_authz.lookup_admission(mixer_authz.verified_identity_v1,mixer_authz.target_v1,mixer_authz.transaction_identity_v1) OWNER TO mixer_hosted_authz_resolver;
ALTER FUNCTION mixer_authz.lock_admission_rows(mixer_authz.verified_identity_v1,mixer_authz.target_v1,mixer_authz.admission_v1,mixer_authz.transaction_identity_v1) OWNER TO mixer_hosted_authz_resolver;
ALTER FUNCTION mixer_authz.decide_current(mixer_authz.verified_identity_v1,mixer_authz.target_v1,mixer_authz.admission_v1,mixer_authz.transaction_identity_v1) OWNER TO mixer_hosted_authz_resolver;
ALTER FUNCTION mixer_authz.recheck_current(mixer_authz.verified_identity_v1,mixer_authz.target_v1,mixer_authz.admission_v1,mixer_authz.transaction_identity_v1) OWNER TO mixer_hosted_authz_resolver;
GRANT EXECUTE ON FUNCTION mixer_authz.finite_uint(numeric,numeric,numeric) TO mixer_hosted_authz_resolver;
GRANT EXECUTE ON FUNCTION mixer_authz.bounded_text(text,integer) TO mixer_hosted_authz_resolver;
GRANT EXECUTE ON FUNCTION mixer_authz.valid_id(text) TO mixer_hosted_authz_resolver;
GRANT EXECUTE ON FUNCTION mixer_authz.validate_inputs(mixer_authz.verified_identity_v1,mixer_authz.target_v1) TO mixer_hosted_authz_resolver;
GRANT EXECUTE ON FUNCTION mixer_authz.assert_transaction(mixer_authz.transaction_identity_v1) TO mixer_hosted_authz_resolver;
GRANT EXECUTE ON FUNCTION mixer_authz.lookup_admission(mixer_authz.verified_identity_v1,mixer_authz.target_v1,mixer_authz.transaction_identity_v1) TO mixer_hosted_runtime;
GRANT EXECUTE ON FUNCTION mixer_authz.lock_admission_rows(mixer_authz.verified_identity_v1,mixer_authz.target_v1,mixer_authz.admission_v1,mixer_authz.transaction_identity_v1) TO mixer_hosted_runtime;
GRANT EXECUTE ON FUNCTION mixer_authz.decide_current(mixer_authz.verified_identity_v1,mixer_authz.target_v1,mixer_authz.admission_v1,mixer_authz.transaction_identity_v1) TO mixer_hosted_runtime;
GRANT EXECUTE ON FUNCTION mixer_authz.recheck_current(mixer_authz.verified_identity_v1,mixer_authz.target_v1,mixer_authz.admission_v1,mixer_authz.transaction_identity_v1) TO mixer_hosted_domain_writer;
GRANT USAGE ON TYPE mixer_authz.verified_identity_v1 TO mixer_hosted_authz_resolver,mixer_hosted_domain_writer,mixer_hosted_runtime;
GRANT USAGE ON TYPE mixer_authz.target_v1 TO mixer_hosted_authz_resolver,mixer_hosted_domain_writer,mixer_hosted_runtime;
GRANT USAGE ON TYPE mixer_authz.transaction_identity_v1 TO mixer_hosted_authz_resolver,mixer_hosted_domain_writer,mixer_hosted_runtime;
GRANT USAGE ON TYPE mixer_authz.admission_v1 TO mixer_hosted_authz_resolver,mixer_hosted_domain_writer,mixer_hosted_runtime;
GRANT USAGE ON TYPE mixer_authz.membership_witness_v1 TO mixer_hosted_authz_resolver,mixer_hosted_domain_writer,mixer_hosted_runtime;
GRANT USAGE ON TYPE mixer_authz.decision_v1 TO mixer_hosted_authz_resolver,mixer_hosted_domain_writer,mixer_hosted_runtime;
COMMIT;
