defmodule MixerHosted.Releases.ReleaseJobs.ProcessorAdmission do
  @moduledoc false
  use GenServer

  alias MixerHosted.Repo

  # Fetch, stage, and acknowledge jobs with Basic; lease leadership with Database.
  # All publication and projection access goes through the one SQL capability.
  @admission_sql """
  WITH surface AS (
    SELECT pg_catalog.to_regclass('mixer_release_jobs.oban_jobs') AS jobs,
           pg_catalog.to_regclass('mixer_release_jobs.oban_peers') AS peers,
           pg_catalog.to_regclass('mixer_release_jobs.offer_materializations') AS projection,
           pg_catalog.to_regprocedure('mixer_release_jobs.materialize_v1(bigint,integer)') AS entry
  ), job_updates(name) AS (
    VALUES ('state'), ('attempt'), ('attempted_at'), ('attempted_by'), ('scheduled_at'),
           ('completed_at'), ('cancelled_at'), ('discarded_at'), ('errors')
  ), isolated_relations AS (
    SELECT c.oid, c.relowner
    FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
    WHERE (n.nspname = 'public' AND c.relname IN (
      'oban_jobs', 'oban_peers', 'mixer_release_heads', 'mixer_release_publications',
      'mixer_release_cli_requests', 'mixer_customer_artifacts'
    )) OR c.oid = (SELECT projection FROM surface)
  )
  SELECT current_user = 'mixer_release_processor' AND current_user = session_user
    AND r.rolcanlogin AND NOT (r.rolsuper OR r.rolbypassrls OR r.rolcreaterole
      OR r.rolcreatedb OR r.rolreplication)
    AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_auth_members m WHERE m.member = r.oid)
    AND NOT pg_catalog.has_database_privilege(current_user, current_database(), 'CREATE')
    AND NOT pg_catalog.has_schema_privilege(current_user, 'public', 'CREATE')
    AND pg_catalog.has_schema_privilege(current_user, 'mixer_release_jobs', 'USAGE')
    AND NOT pg_catalog.has_schema_privilege(current_user, 'mixer_release_jobs', 'CREATE')
    AND s.projection IS NOT NULL
    AND pg_catalog.obj_description(s.jobs, 'pg_class') = '14'
    AND pg_catalog.has_table_privilege(current_user, s.jobs, 'SELECT')
    AND NOT pg_catalog.has_table_privilege(current_user, s.jobs, 'DELETE,TRUNCATE,TRIGGER')
    AND NOT pg_catalog.has_any_column_privilege(current_user, s.jobs, 'INSERT,REFERENCES')
    AND NOT EXISTS (
      SELECT 1 FROM job_updates u
      WHERE NOT pg_catalog.has_column_privilege(current_user, s.jobs, u.name, 'UPDATE')
    )
    AND NOT EXISTS (
      SELECT 1 FROM pg_catalog.pg_attribute a
      WHERE a.attrelid = s.jobs AND a.attnum > 0 AND NOT a.attisdropped
        AND NOT EXISTS (SELECT 1 FROM job_updates u WHERE u.name = a.attname)
        AND pg_catalog.has_column_privilege(current_user, s.jobs, a.attnum, 'UPDATE')
    )
    AND pg_catalog.has_table_privilege(current_user, s.peers, 'SELECT')
    AND pg_catalog.has_table_privilege(current_user, s.peers, 'DELETE')
    AND NOT pg_catalog.has_table_privilege(current_user, s.peers,
      'TRUNCATE,TRIGGER,SELECT WITH GRANT OPTION,DELETE WITH GRANT OPTION')
    AND NOT pg_catalog.has_any_column_privilege(current_user, s.peers, 'REFERENCES')
    AND pg_catalog.has_column_privilege(current_user, s.peers, 'expires_at', 'UPDATE')
    AND NOT EXISTS (
      SELECT 1 FROM (VALUES ('name'), ('node'), ('started_at'), ('expires_at')) c(name)
      WHERE NOT pg_catalog.has_column_privilege(current_user, s.peers, c.name, 'INSERT')
    )
    AND NOT EXISTS (
      SELECT 1 FROM pg_catalog.pg_attribute a
      WHERE a.attrelid = s.peers AND a.attnum > 0 AND NOT a.attisdropped
        AND (
          (a.attname NOT IN ('name', 'node', 'started_at', 'expires_at')
            AND pg_catalog.has_column_privilege(current_user, s.peers, a.attnum, 'INSERT'))
          OR (a.attname <> 'expires_at'
            AND pg_catalog.has_column_privilege(current_user, s.peers, a.attnum, 'UPDATE'))
          OR pg_catalog.has_column_privilege(current_user, s.peers, a.attnum,
            'SELECT WITH GRANT OPTION,INSERT WITH GRANT OPTION,UPDATE WITH GRANT OPTION')
        )
    )
    AND NOT EXISTS (
      SELECT 1 FROM isolated_relations c WHERE pg_catalog.pg_has_role(current_user, c.relowner, 'MEMBER')
        OR pg_catalog.has_any_column_privilege(current_user, c.oid, 'SELECT,INSERT,UPDATE,REFERENCES')
        OR pg_catalog.has_table_privilege(current_user, c.oid, 'DELETE,TRUNCATE,TRIGGER')
    )
    AND p.prosecdef AND p.prorettype = 'pg_catalog.text'::regtype AND NOT p.proretset
    AND NOT pg_catalog.pg_has_role(current_user, p.proowner, 'MEMBER')
    AND pg_catalog.has_function_privilege(current_user, p.oid, 'EXECUTE')
    AND NOT pg_catalog.has_function_privilege(current_user, p.oid, 'EXECUTE WITH GRANT OPTION')
    AND NOT EXISTS (
      SELECT 1 FROM pg_catalog.aclexplode(COALESCE(p.proacl, pg_catalog.acldefault('f', p.proowner))) a
      WHERE a.grantee = 0 AND a.privilege_type = 'EXECUTE'
    )
  FROM surface s JOIN pg_catalog.pg_proc p ON p.oid = s.entry
  JOIN pg_catalog.pg_roles r ON r.rolname = current_user
  """

  def start_link(:releases_v1), do: GenServer.start_link(__MODULE__, :releases_v1)

  @impl true
  def init(:releases_v1) do
    case Repo.query(@admission_sql, [], timeout: 5_000) do
      {:ok, %{rows: [[true]]}} -> {:ok, :admitted}
      _ -> {:stop, :release_processor_admission_refused}
    end
  end

  def after_connect(connection) do
    case Postgrex.query(connection, @admission_sql, [], timeout: 5_000) do
      {:ok, %{rows: [[true]]}} -> :ok
      _ -> raise "release processor admission refused"
    end
  end
end
