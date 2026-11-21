\set ON_ERROR_STOP on

-- Apply migration 20261120000014 as the release ledger owner. The owner needs
-- CREATE on this database for the dedicated schema. Then run this script with
-- psql as the local database administrator with access to the FORCE-RLS head.
-- From hosted/: mix ecto.migrate --migrations-path priv/local_release_jobs --to 20261120000014
-- The registered release heads select the writers. Use a separate password for
-- mixer_release_processor and supply it via MIXER_DATABASE_PASSWORD.
-- The processor uses MIXER_HOSTED_ROLE=processor, MIXER_PROCESSOR_PROFILE=releases_v1,
-- and MIXER_DATABASE_USER=mixer_release_processor, against this same database.
-- Database peer leadership and staging coordinate this release queue.
-- Pruning is disabled.
-- The API opts in with MIXER_LOCAL_RELEASE_JOBS_ENABLED=true.
BEGIN;

LOCK TABLE public.mixer_release_heads IN SHARE MODE;

DO $body$
BEGIN
  IF NOT EXISTS (SELECT FROM public.mixer_release_heads) OR EXISTS (
    SELECT FROM public.mixer_release_heads h
    LEFT JOIN pg_catalog.pg_roles r ON r.rolname = h.writer_role
    WHERE r.oid IS NULL OR r.rolname = 'mixer_release_processor'
      OR NOT r.rolcanlogin OR r.rolsuper OR r.rolbypassrls OR r.rolcreaterole
      OR r.rolcreatedb OR r.rolreplication
      OR pg_catalog.pg_has_role(r.oid, (
        SELECT relowner FROM pg_catalog.pg_class WHERE oid = 'public.mixer_release_heads'::regclass
      ), 'MEMBER')
      OR pg_catalog.has_column_privilege(r.oid, 'public.mixer_release_publications',
        'release_jobs_xact_id', 'INSERT')
      OR pg_catalog.has_any_column_privilege(r.oid, 'public.mixer_release_publications', 'UPDATE')
      OR pg_catalog.has_schema_privilege(r.oid, 'mixer_release_jobs', 'CREATE')
  ) THEN
    RAISE EXCEPTION 'release queue requires registered restricted writer logins';
  END IF;
END
$body$;

SELECT NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'mixer_release_processor')
  AS create_release_processor
\gset

\if :create_release_processor
  CREATE ROLE mixer_release_processor LOGIN NOINHERIT NOSUPERUSER
    NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
\endif

-- An empty schema rollback preserves the processor login. Check an existing
-- login before restoring grants and leave its password intact.
DO $body$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_catalog.pg_roles r
    WHERE r.rolname = 'mixer_release_processor' AND r.rolcanlogin
      AND NOT (r.rolinherit OR r.rolsuper OR r.rolbypassrls OR r.rolcreatedb
        OR r.rolcreaterole OR r.rolreplication)
      AND NOT EXISTS (SELECT FROM pg_catalog.pg_auth_members m WHERE r.oid IN (m.member,m.roleid))
      AND NOT EXISTS (
        SELECT FROM pg_catalog.pg_shdepend d
        WHERE d.refclassid = 'pg_catalog.pg_authid'::regclass AND d.refobjid = r.oid AND d.deptype = 'o'
      )
      AND NOT pg_catalog.has_database_privilege(r.oid, current_database(), 'CREATE')
      AND NOT EXISTS (
        SELECT FROM pg_catalog.pg_namespace n WHERE pg_catalog.has_schema_privilege(r.oid,n.oid,'CREATE')
      )
      AND NOT EXISTS (
        SELECT FROM pg_catalog.pg_class c WHERE c.oid IN ('public.mixer_release_publications'::regclass,
          'public.mixer_release_heads'::regclass, 'public.mixer_customer_artifacts'::regclass)
        AND (pg_catalog.has_any_column_privilege(r.oid,c.oid,'SELECT,INSERT,UPDATE,REFERENCES')
          OR pg_catalog.has_table_privilege(r.oid,c.oid,'DELETE,TRUNCATE,TRIGGER'))
      )
  ) THEN
    RAISE EXCEPTION 'unsafe release processor login';
  END IF;
END
$body$;

GRANT CONNECT ON DATABASE :"DBNAME" TO mixer_release_processor;
GRANT USAGE ON SCHEMA mixer_release_jobs TO mixer_release_processor;

SELECT pg_catalog.format('GRANT USAGE ON SCHEMA mixer_release_jobs TO %I', writer_role),
       pg_catalog.format('GRANT INSERT (queue, worker, args), SELECT (id)
         ON mixer_release_jobs.oban_jobs TO %I', writer_role),
       pg_catalog.format('GRANT USAGE ON SEQUENCE mixer_release_jobs.oban_jobs_id_seq TO %I', writer_role),
       pg_catalog.format('GRANT EXECUTE ON FUNCTION mixer_release_jobs.writer_can_enqueue_v1(jsonb)
         TO %I', writer_role)
FROM (SELECT DISTINCT writer_role FROM public.mixer_release_heads) writers
\gexec

SELECT string_agg(DISTINCT quote_ident(writer_role::text), ', ' ORDER BY quote_ident(writer_role::text))
  AS release_jobs_writers
FROM public.mixer_release_heads
\gset

SELECT pg_catalog.format('DROP POLICY %I ON mixer_release_jobs.oban_jobs', polname)
FROM pg_catalog.pg_policy
WHERE polrelid = 'mixer_release_jobs.oban_jobs'::regclass
  AND polname IN ('release_job_writer_insert', 'release_job_writer_returning')
\gexec

CREATE POLICY release_job_writer_insert ON mixer_release_jobs.oban_jobs FOR INSERT TO :release_jobs_writers
WITH CHECK (
  queue = 'releases' AND worker = 'MixerHosted.Releases.ReleaseJobs.Materialize'
  AND state = 'available' AND attempt = 0 AND mixer_release_jobs.writer_can_enqueue_v1(args)
);

CREATE POLICY release_job_writer_returning ON mixer_release_jobs.oban_jobs FOR SELECT TO :release_jobs_writers
USING (
  queue = 'releases' AND worker = 'MixerHosted.Releases.ReleaseJobs.Materialize'
  AND state = 'available' AND attempt = 0 AND mixer_release_jobs.writer_can_enqueue_v1(args)
);

GRANT SELECT ON mixer_release_jobs.oban_jobs TO mixer_release_processor;
GRANT UPDATE (state, attempt, attempted_at, attempted_by, scheduled_at,
  completed_at, discarded_at, cancelled_at, errors)
  ON mixer_release_jobs.oban_jobs TO mixer_release_processor;
GRANT SELECT, INSERT (name, node, started_at, expires_at), DELETE, UPDATE (expires_at)
  ON mixer_release_jobs.oban_peers TO mixer_release_processor;
GRANT EXECUTE ON FUNCTION mixer_release_jobs.materialize_v1(bigint, integer) TO mixer_release_processor;

COMMIT;
