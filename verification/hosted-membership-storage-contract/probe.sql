-- Disposable privilege/locking pattern probe, NOT a hosted migration.
CREATE ROLE probe_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE probe_resolver NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE probe_runtime LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE probe_bypass LOGIN BYPASSRLS;
CREATE ROLE probe_bridge NOLOGIN NOINHERIT;
CREATE ROLE probe_chain LOGIN NOINHERIT;
GRANT probe_owner TO probe_bridge WITH INHERIT FALSE, SET TRUE;
GRANT probe_bridge TO probe_chain WITH INHERIT FALSE, SET TRUE;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
CREATE SCHEMA probe_auth AUTHORIZATION probe_owner;
CREATE SCHEMA probe_domain AUTHORIZATION probe_owner;
GRANT USAGE ON SCHEMA probe_auth, probe_domain TO probe_resolver, probe_runtime;
SET ROLE probe_owner;
CREATE TABLE probe_auth.profiles(id text PRIMARY KEY, active boolean NOT NULL, revision bigint NOT NULL);
CREATE TABLE probe_auth.principals(LIKE probe_auth.profiles INCLUDING ALL);
CREATE TABLE probe_auth.families(LIKE probe_auth.profiles INCLUDING ALL);
CREATE TABLE probe_auth.org_heads(LIKE probe_auth.profiles INCLUDING ALL);
CREATE TABLE probe_auth.project_heads(LIKE probe_auth.profiles INCLUDING ALL);
CREATE TABLE probe_auth.memberships(principal text NOT NULL, org text NOT NULL, project text NOT NULL, role text NOT NULL, active boolean NOT NULL);
CREATE TABLE probe_auth.recursive_members(principal text PRIMARY KEY);
CREATE TABLE probe_domain.artifacts(org text NOT NULL, project text NOT NULL, digest text NOT NULL, PRIMARY KEY(org,project,digest));
INSERT INTO probe_auth.profiles VALUES ('p',true,1);
INSERT INTO probe_auth.principals VALUES ('p',true,1);
INSERT INTO probe_auth.families VALUES ('p',true,1);
INSERT INTO probe_auth.org_heads VALUES ('a',true,1);
INSERT INTO probe_auth.project_heads VALUES ('a/p',true,1);
INSERT INTO probe_auth.memberships VALUES ('p','a','p','viewer',true);
INSERT INTO probe_auth.recursive_members VALUES ('p');
INSERT INTO probe_domain.artifacts VALUES ('a','p','digest-a'),('b','p','digest-b');
RESET ROLE;
DO $$ DECLARE t text; BEGIN
  FOREACH t IN ARRAY ARRAY['profiles','principals','families','org_heads','project_heads','memberships'] LOOP
    EXECUTE format('ALTER TABLE probe_auth.%I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE probe_auth.%I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format('CREATE POLICY resolver_read ON probe_auth.%I FOR SELECT TO probe_resolver USING (true)', t);
    EXECUTE format('GRANT SELECT ON probe_auth.%I TO probe_resolver', t);
  END LOOP;
END $$;
ALTER TABLE probe_auth.recursive_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE probe_auth.recursive_members FORCE ROW LEVEL SECURITY;
CREATE POLICY recursive_bad ON probe_auth.recursive_members TO probe_runtime USING (EXISTS(SELECT 1 FROM probe_auth.recursive_members m WHERE m.principal=current_setting('probe.principal',true)));
GRANT SELECT ON probe_auth.recursive_members TO probe_runtime;
-- Creation is performed by disposable bootstrap. Owner has no CREATE afterward.
CREATE FUNCTION probe_auth.lock_chain() RETURNS integer LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog SET row_security=on AS $$
BEGIN
  PERFORM 1 FROM probe_auth.profiles WHERE id='p' FOR SHARE;
  IF NOT FOUND THEN RAISE EXCEPTION 'missing profile lock row' USING ERRCODE='P0002'; END IF;
  PERFORM 1 FROM probe_auth.principals WHERE id='p' FOR SHARE;
  IF NOT FOUND THEN RAISE EXCEPTION 'missing principal lock row' USING ERRCODE='P0002'; END IF;
  PERFORM 1 FROM probe_auth.families WHERE id='p' FOR SHARE;
  IF NOT FOUND THEN RAISE EXCEPTION 'missing family lock row' USING ERRCODE='P0002'; END IF;
  PERFORM 1 FROM probe_auth.org_heads WHERE id='a' FOR SHARE;
  IF NOT FOUND THEN RAISE EXCEPTION 'missing organization lock row' USING ERRCODE='P0002'; END IF;
  PERFORM 1 FROM probe_auth.project_heads WHERE id='a/p' FOR SHARE;
  IF NOT FOUND THEN RAISE EXCEPTION 'missing project lock row' USING ERRCODE='P0002'; END IF;
  RETURN 5;
END $$;
ALTER FUNCTION probe_auth.lock_chain() OWNER TO probe_resolver;
REVOKE ALL ON FUNCTION probe_auth.lock_chain() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION probe_auth.lock_chain() TO probe_runtime;
CREATE FUNCTION probe_auth.can_read(o text,p text) RETURNS boolean LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path=pg_catalog SET row_security=on AS $$
 SELECT coalesce(current_setting('probe.action',true)='artifact.read'
   AND current_setting('probe.org',true)=o AND current_setting('probe.project',true)=p
   AND EXISTS(SELECT 1 FROM probe_auth.profiles WHERE id='p' AND active)
   AND EXISTS(SELECT 1 FROM probe_auth.principals WHERE id=current_setting('probe.principal',true) AND active)
   AND EXISTS(SELECT 1 FROM probe_auth.families WHERE id='p' AND active)
   AND EXISTS(SELECT 1 FROM probe_auth.memberships m WHERE m.principal=current_setting('probe.principal',true) AND m.org=o AND m.project=p AND m.active AND m.role='viewer'),false)
$$;
ALTER FUNCTION probe_auth.can_read(text,text) OWNER TO probe_resolver;
REVOKE ALL ON FUNCTION probe_auth.can_read(text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION probe_auth.can_read(text,text) TO probe_runtime;
ALTER TABLE probe_domain.artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE probe_domain.artifacts FORCE ROW LEVEL SECURITY;
CREATE POLICY runtime_read ON probe_domain.artifacts FOR SELECT TO probe_runtime USING (probe_auth.can_read(org,project));
GRANT SELECT ON probe_domain.artifacts TO probe_runtime;
