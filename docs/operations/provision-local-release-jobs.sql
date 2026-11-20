\set ON_ERROR_STOP on

-- Apply migration 20261120000014 as the release ledger owner. The owner needs
-- CREATE on this database for the dedicated schema. Then run this script with
-- psql as the local database administrator with access to the FORCE-RLS head.
-- From hosted/: mix ecto.migrate --migrations-path priv/local_release_jobs --to 20261120000014
-- The registered release target selects the writer. Use a separate password for
-- mixer_release_processor and supply it via MIXER_DATABASE_PASSWORD.
-- The processor uses MIXER_HOSTED_ROLE=processor, MIXER_PROCESSOR_PROFILE=releases_v1,
-- and MIXER_DATABASE_USER=mixer_release_processor, against this same database.
-- Use Oban.Peers.Isolated and Oban.Notifiers.Isolated with staging enabled
-- and pruning disabled.
-- The API opts in with MIXER_LOCAL_RELEASE_JOBS_ENABLED=true.
BEGIN;

SELECT h.writer_role::text AS release_jobs_writer
FROM public.mixer_release_heads h
JOIN pg_catalog.pg_roles r ON r.rolname = h.writer_role
WHERE r.rolcanlogin AND NOT (r.rolsuper OR r.rolbypassrls OR r.rolcreaterole
  OR r.rolcreatedb OR r.rolreplication)
  AND NOT pg_catalog.has_column_privilege(r.oid, 'public.mixer_release_publications',
    'release_jobs_xact_id', 'INSERT')
  AND NOT pg_catalog.has_any_column_privilege(r.oid, 'public.mixer_release_publications', 'UPDATE')
  AND NOT pg_catalog.has_schema_privilege(r.oid, 'mixer_release_jobs', 'CREATE')
\gset

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
GRANT USAGE ON SCHEMA mixer_release_jobs TO :"release_jobs_writer", mixer_release_processor;

GRANT INSERT (queue, worker, args), SELECT (id)
  ON mixer_release_jobs.oban_jobs TO :"release_jobs_writer";
GRANT USAGE ON SEQUENCE mixer_release_jobs.oban_jobs_id_seq TO :"release_jobs_writer";
GRANT EXECUTE ON FUNCTION mixer_release_jobs.writer_can_enqueue_v1(jsonb) TO :"release_jobs_writer";

CREATE POLICY release_job_writer_insert ON mixer_release_jobs.oban_jobs FOR INSERT TO :"release_jobs_writer"
WITH CHECK (
  queue = 'releases' AND worker = 'MixerHosted.Releases.ReleaseJobs.Materialize'
  AND state = 'available' AND attempt = 0 AND mixer_release_jobs.writer_can_enqueue_v1(args)
);

CREATE POLICY release_job_writer_returning ON mixer_release_jobs.oban_jobs FOR SELECT TO :"release_jobs_writer"
USING (
  queue = 'releases' AND worker = 'MixerHosted.Releases.ReleaseJobs.Materialize'
  AND state = 'available' AND attempt = 0 AND mixer_release_jobs.writer_can_enqueue_v1(args)
);

GRANT SELECT ON mixer_release_jobs.oban_jobs TO mixer_release_processor;
GRANT UPDATE (state, attempt, attempted_at, attempted_by, scheduled_at,
  completed_at, discarded_at, cancelled_at, errors)
  ON mixer_release_jobs.oban_jobs TO mixer_release_processor;
GRANT EXECUTE ON FUNCTION mixer_release_jobs.materialize_v1(bigint, integer) TO mixer_release_processor;

COMMIT;
