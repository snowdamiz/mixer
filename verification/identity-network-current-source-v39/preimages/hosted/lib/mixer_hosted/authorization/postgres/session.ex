defmodule MixerHosted.Authorization.Postgres.Session do
  @moduledoc false

  @tables ~w(profiles principals bindings families credentials organizations projects applications environments organization_heads project_heads memberships)
  @locks ~w(profiles principals families credentials organization_heads project_heads)

  def prepare!(repo, lookup) do
    linkage = prepare_identity_scope!(repo, lookup.identity, lookup.target)
    lock!(repo, "organization_heads", :not_found)
    lock!(repo, "project_heads", :not_found)
    linkage
  end

  # Read-only directory callers must separately validate current identity state,
  # select and lock their bounded tenant rows, and recheck before commit. This
  # helper supplies only linkage and identity locks, never artifact authority.
  def prepare_identity!(repo, identity) do
    prepare_identity_scope!(repo, identity, %{
      organization_id: nil,
      project_id: nil,
      application_id: nil,
      environment_id: nil
    })
  end

  defp prepare_identity_scope!(repo, i, scope) do
    if not repo.in_transaction?(), do: repo.rollback(:authorization_unavailable)

    query!(repo, "SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
    query!(repo, "SET LOCAL statement_timeout = '5000ms'")
    query!(repo, "SET LOCAL lock_timeout = '500ms'")
    query!(repo, "SET LOCAL idle_in_transaction_session_timeout = '5000ms'")
    # These bounded authorization reads must not pay LLVM compilation cost for
    # RLS-expanded plans. LOCAL restores the connection's prior policy at either
    # transaction outcome; never change a pooled connection's session policy.
    query!(repo, "SET LOCAL jit = off")

    case query!(repo, "SELECT pg_catalog.current_setting('jit')").rows do
      [["off"]] -> :ok
      _ -> repo.rollback(:authorization_unavailable)
    end

    topology!(repo)

    context!(repo,
      profile_id: i.profile_id,
      profile_version: Integer.to_string(i.profile_version),
      issuer: i.issuer,
      subject: i.subject,
      client_id: i.client_id,
      identity_class: "human",
      credential_ref: i.credential_ref,
      organization_id: scope.organization_id,
      project_id: scope.project_id,
      application_id: scope.application_id,
      environment_id: scope.environment_id,
      principal_id: nil,
      family_id: nil,
      directory_mode: nil
    )

    lock!(repo, "profiles", :unauthenticated)

    principal =
      one!(repo, "SELECT principal_id FROM public.mixer_authz_bindings", [], :unauthenticated)
      |> hd()

    context!(repo, principal_id: principal)
    lock!(repo, "principals", :unauthenticated)

    [^principal, family] =
      one!(
        repo,
        "SELECT principal_id, family_id FROM public.mixer_authz_credentials",
        [],
        :unauthenticated
      )

    context!(repo, family_id: family)
    lock!(repo, "families", :unauthenticated)
    lock!(repo, "credentials", :unauthenticated)
    %{principal_id: principal, family_id: family}
  end

  def finish!(repo), do: query!(repo, "SELECT 1")

  def context!(repo, entries) do
    Enum.each(entries, fn {key, value} ->
      query!(repo, "SELECT pg_catalog.set_config($1, $2, true)", [
        "mixer.authz.#{key}",
        value || ""
      ])
    end)
  end

  def query!(repo, sql, params \\ []),
    do: Ecto.Adapters.SQL.query!(repo, sql, params, timeout: 5_000, queue: false)

  def one!(repo, sql, params, error) do
    case query!(repo, sql, params).rows do
      [row] -> row
      _ -> repo.rollback(error)
    end
  end

  defp lock!(repo, table, error) when table in @locks do
    case query!(repo, "SELECT public.mixer_authz_lock_#{table}()").rows do
      [[true]] -> :ok
      _ -> repo.rollback(error)
    end
  end

  defp topology!(repo) do
    # Check the effective login and every reachable privileged/owner role. The
    # runtime cannot SET ROLE back to an owner, bypass RLS, or perform authz DML.
    [[safe_role]] =
      query!(repo, """
      SELECT current_user = session_user AND NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_roles r
        WHERE pg_catalog.pg_has_role(current_user, r.oid, 'MEMBER')
          AND (r.rolsuper OR r.rolbypassrls OR r.rolcreaterole OR r.rolcreatedb OR r.rolreplication
            OR pg_catalog.substr(r.rolname::text, 1, 3) = 'pg_'))
      """).rows

    tables = Enum.map(@tables, &("mixer_authz_" <> &1))

    [[count, safe_tables]] =
      query!(
        repo,
        """
        SELECT count(*), bool_and(c.relrowsecurity AND c.relforcerowsecurity
          AND NOT owner.rolcanlogin AND NOT owner.rolsuper AND NOT owner.rolbypassrls
          AND NOT pg_catalog.pg_has_role(current_user, c.relowner, 'MEMBER')
          AND pg_catalog.has_table_privilege(current_user, c.oid, 'SELECT')
          AND NOT pg_catalog.has_table_privilege(current_user, c.oid, 'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
          AND NOT pg_catalog.has_any_column_privilege(current_user, c.oid, 'INSERT,UPDATE,REFERENCES'))
        FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        JOIN pg_catalog.pg_roles owner ON owner.oid = c.relowner
        WHERE n.nspname = 'public' AND c.relname = ANY($1::text[]) AND c.relkind = 'r'
        """,
        [tables]
      ).rows

    functions = Enum.map(@locks, &("mixer_authz_lock_" <> &1))

    [[function_count, safe_functions]] =
      query!(
        repo,
        """
        SELECT count(*), bool_and(p.prosecdef AND p.pronargs = 0
          AND p.proconfig = ARRAY['search_path=pg_catalog']::text[]
          AND NOT owner.rolcanlogin AND NOT owner.rolsuper AND NOT owner.rolbypassrls
          AND NOT pg_catalog.pg_has_role(current_user, p.proowner, 'MEMBER')
          AND pg_catalog.has_function_privilege(current_user, p.oid, 'EXECUTE')
          AND NOT EXISTS (SELECT 1 FROM pg_catalog.aclexplode(
            COALESCE(p.proacl, pg_catalog.acldefault('f', p.proowner))) a
            WHERE a.grantee = 0 AND a.privilege_type = 'EXECUTE'))
        FROM pg_catalog.pg_proc p
        JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
        JOIN pg_catalog.pg_roles owner ON owner.oid = p.proowner
        WHERE n.nspname = 'public' AND p.proname = ANY($1::text[])
        """,
        [functions]
      ).rows

    if safe_role and count == length(@tables) and safe_tables and
         function_count == length(@locks) and safe_functions do
      :ok
    else
      repo.rollback(:authorization_unavailable)
    end
  end
end
