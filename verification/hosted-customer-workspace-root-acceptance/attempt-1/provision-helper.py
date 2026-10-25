def provision_customer_artifact_fixtures(pg_bin, port, run_command):
    """Isolated customer storage, metadata-resolution and application fixtures."""
    env = {}
    for prefix, database, variable in [
        ("storage", "mixer_customer_artifact_storage", "MIXER_ARTIFACT_STORAGE_TEST_PORT"),
        ("read_scope", "mixer_artifact_read_scope", "MIXER_ARTIFACT_READ_SCOPE_TEST_PORT"),
        ("facade", "mixer_customer_artifact_facade", "MIXER_ARTIFACT_FACADE_TEST_PORT"),
        ("http_artifact", "mixer_customer_artifact_http", "MIXER_ARTIFACT_HTTP_TEST_PORT"),
        ("workspace", "mixer_customer_workspace", "MIXER_WORKSPACE_TEST_PORT"),
        ("workspace_http", "mixer_customer_workspace_http", "MIXER_WORKSPACE_HTTP_TEST_PORT"),
    ]:
        psql = [str(pg_bin / "psql"), "-X", "-h", "127.0.0.1", "-p", str(port),
                "-U", "mixer_fixture", "-v", "ON_ERROR_STOP=1"]
        run_command(prefix + "-fixture-roles", psql + ["-d", "postgres", "-c",
            f"CREATE ROLE {prefix}_fixture_admin LOGIN SUPERUSER; "
            f"CREATE ROLE {prefix}_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS; "
            f"CREATE ROLE {prefix}_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;"])
        run_command(prefix + "-fixture-database", [str(pg_bin / "createdb"), "-h", "127.0.0.1", "-p", str(port),
            "-U", "mixer_fixture", "-O", prefix + "_fixture_admin", database])
        run_command(prefix + "-fixture-grants", psql + ["-d", database, "-c",
            "REVOKE CREATE ON SCHEMA public FROM PUBLIC; "
            f"ALTER SCHEMA public OWNER TO {prefix}_owner; "
            f"GRANT USAGE ON SCHEMA public TO {prefix}_runtime;"])
        env[variable] = str(port)
    return env
