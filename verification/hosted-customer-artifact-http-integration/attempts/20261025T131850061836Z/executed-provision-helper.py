def provision_customer_artifact_fixtures(pg_bin, port, run_command):
    """Isolated artifact storage, metadata-resolution and application fixtures."""
    env = {}
    for prefix, database, variable in [('http_artifact', 'mixer_customer_artifact_http', 'MIXER_ARTIFACT_HTTP_TEST_PORT')]:
        psql = [str(pg_bin / 'psql'), '-X', '-h', '127.0.0.1', '-p', str(port), '-U', 'mixer_fixture', '-v', 'ON_ERROR_STOP=1']
        run_command(prefix + '-fixture-roles', psql + ['-d', 'postgres', '-c', f'CREATE ROLE {prefix}_fixture_admin LOGIN SUPERUSER; CREATE ROLE {prefix}_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS; CREATE ROLE {prefix}_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;'])
        run_command(prefix + '-fixture-database', [str(pg_bin / 'createdb'), '-h', '127.0.0.1', '-p', str(port), '-U', 'mixer_fixture', '-O', prefix + '_fixture_admin', database])
        run_command(prefix + '-fixture-grants', psql + ['-d', database, '-c', f'REVOKE CREATE ON SCHEMA public FROM PUBLIC; ALTER SCHEMA public OWNER TO {prefix}_owner; GRANT USAGE ON SCHEMA public TO {prefix}_runtime;'])
        env[variable] = str(port)
    return env
