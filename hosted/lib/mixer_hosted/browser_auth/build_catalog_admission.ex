defmodule MixerHosted.BrowserAuth.BuildCatalogAdmission do
  @moduledoc false
  alias MixerHosted.CustomerBuildCatalog.Schema
  alias MixerHosted.BrowserAuth.RelationCatalog.Unavailable

  # Fixed metadata only. Never executes the capabilities as the lifecycle login.
  def check!(repo, roles, deadline) do
    true = repo.in_transaction?()

    %{rows: [[backend, 17]]} =
      query!(
        repo,
        deadline,
        "SELECT pg_catalog.pg_backend_pid(), pg_catalog.current_setting('server_version_num')::integer / 10000",
        []
      )

    contract = Schema.surface_contract()
    role = contract.role
    ordinary = roles.ordinary_runtime_login
    owner = roles.relation_owner
    true = role not in Map.values(roles)

    safe!(
      repo,
      deadline,
      backend,
      """
      SELECT count(*)=1 AND bool_and(NOT r.rolcanlogin AND NOT r.rolsuper AND NOT r.rolbypassrls
        AND NOT r.rolcreatedb AND NOT r.rolcreaterole AND NOT r.rolreplication AND NOT r.rolinherit
        AND r.rolconfig IS NULL AND r.rolconnlimit=-1 AND r.rolvaliduntil IS NULL
        AND NOT EXISTS(SELECT 1 FROM pg_catalog.pg_auth_members WHERE member=r.oid OR roleid=r.oid)
        AND NOT EXISTS(SELECT 1 FROM pg_catalog.pg_shdepend d
          WHERE d.refclassid='pg_catalog.pg_authid'::regclass AND d.refobjid=r.oid AND d.deptype='o'
          AND NOT (d.dbid=(SELECT oid FROM pg_catalog.pg_database WHERE datname=pg_catalog.current_database())
            AND d.classid='pg_catalog.pg_proc'::regclass AND d.objid IN
              (SELECT p.oid FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
                WHERE n.nspname='public' AND p.proname=ANY($2::text[]) AND p.proowner=r.oid)))
        AND (SELECT count(*) FROM pg_catalog.pg_proc WHERE proowner=r.oid)=2
        AND NOT EXISTS(SELECT 1 FROM pg_catalog.pg_namespace n WHERE pg_catalog.has_schema_privilege(r.oid,n.oid,'CREATE'))
        AND NOT EXISTS(SELECT 1 FROM pg_catalog.pg_database d WHERE d.datdba=r.oid OR pg_catalog.has_database_privilege(r.oid,d.oid,'CREATE')))
      FROM pg_catalog.pg_roles r WHERE r.rolname=$1
      """,
      [role, Enum.map(contract.functions, & &1.name)]
    )

    for function <- contract.functions do
      safe!(
        repo,
        deadline,
        backend,
        """
        SELECT count(*)=1 AND bool_and(p.prosrc=$1 AND p.prosecdef AND p.provolatile='v'
          AND p.prorettype='pg_catalog.jsonb'::regtype AND p.proconfig=ARRAY['search_path=pg_catalog']::text[]
          AND pg_catalog.pg_get_function_identity_arguments(p.oid)=$3
          AND pg_catalog.oidvectortypes(p.proargtypes)=$3
          AND p.pronargs=$6 AND p.pronargdefaults=0 AND p.proargdefaults IS NULL
          AND p.proargnames IS NULL AND p.proallargtypes IS NULL AND p.proargmodes IS NULL
          AND p.provariadic=0 AND p.prokind='f' AND NOT p.proretset AND NOT p.proisstrict
          AND NOT p.proleakproof AND p.proparallel='u' AND p.prosupport=0
          AND p.prosqlbody IS NULL AND p.procost=100 AND p.prorows=0
          AND l.lanname='plpgsql' AND r.rolname=$4
          AND (SELECT count(*) FROM pg_catalog.aclexplode(COALESCE(p.proacl,pg_catalog.acldefault('f',p.proowner))))=2
          AND NOT EXISTS(SELECT 1 FROM pg_catalog.aclexplode(COALESCE(p.proacl,pg_catalog.acldefault('f',p.proowner))) a
            WHERE a.privilege_type<>'EXECUTE' OR a.is_grantable OR a.grantor<>p.proowner
              OR a.grantee NOT IN(p.proowner,(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=$5)))
          AND NOT pg_catalog.has_function_privilege(current_user,p.oid,'EXECUTE'))
        FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
          JOIN pg_catalog.pg_roles r ON r.oid=p.proowner JOIN pg_catalog.pg_language l ON l.oid=p.prolang
        WHERE n.nspname='public' AND p.proname=$2
        """,
        [
          function.body,
          function.name,
          String.replace(function.signature, ",", ", "),
          role,
          ordinary,
          length(String.split(function.signature, ","))
        ]
      )
    end

    # Compare the complete dedicated-role table ACL multiset, across every schema.
    relations = Enum.map(contract.grants, &elem(&1, 0))
    privileges = Enum.map(contract.grants, &elem(&1, 1))

    safe!(
      repo,
      deadline,
      backend,
      """
      WITH role AS (SELECT oid FROM pg_catalog.pg_roles WHERE rolname=$1),
      expected AS (SELECT g.relation,g.privilege,r.oid AS grantee,o.oid AS grantor,false AS option
        FROM ROWS FROM (pg_catalog.unnest($2::text[]),pg_catalog.unnest($3::text[])) g(relation,privilege)
        CROSS JOIN role r CROSS JOIN pg_catalog.pg_roles o WHERE o.rolname=$4),
      actual AS (SELECT n.nspname::text||'.'||c.relname::text AS relation,a.privilege_type AS privilege,
          a.grantee,a.grantor,a.is_grantable AS option
        FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
        CROSS JOIN LATERAL pg_catalog.aclexplode(c.relacl) a WHERE a.grantee=(SELECT oid FROM role))
      SELECT NOT EXISTS((TABLE expected EXCEPT ALL TABLE actual) UNION ALL (TABLE actual EXCEPT ALL TABLE expected))
        AND NOT EXISTS(SELECT 1 FROM pg_catalog.pg_attribute c
          CROSS JOIN LATERAL pg_catalog.aclexplode(c.attacl) a WHERE a.grantee=(SELECT oid FROM role))
        AND NOT EXISTS(SELECT 1 FROM pg_catalog.pg_default_acl d
          CROSS JOIN LATERAL pg_catalog.aclexplode(d.defaclacl) a
          WHERE d.defaclrole=(SELECT oid FROM role) OR a.grantee=(SELECT oid FROM role))
      """,
      [role, relations, privileges, owner]
    )

    safe!(
      repo,
      deadline,
      backend,
      """
      SELECT NOT EXISTS(SELECT 1 FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
        CROSS JOIN pg_catalog.pg_roles r WHERE r.rolname=$1 AND n.nspname<>'information_schema'
        AND pg_catalog.left(n.nspname::text,3)<>'pg_' AND c.relkind IN('r','p','v','m','f','S') AND
        CASE WHEN c.relkind='S' THEN pg_catalog.has_sequence_privilege(r.oid,c.oid,'SELECT,UPDATE,USAGE') ELSE
          pg_catalog.has_table_privilege(r.oid,c.oid,'INSERT,DELETE,TRUNCATE,REFERENCES,TRIGGER,MAINTAIN')
          OR pg_catalog.has_any_column_privilege(r.oid,c.oid,'INSERT,REFERENCES')
          OR (pg_catalog.has_table_privilege(r.oid,c.oid,'SELECT') IS DISTINCT FROM
            (n.nspname::text||'.'||c.relname::text=ANY($2::text[])))
          OR (pg_catalog.has_table_privilege(r.oid,c.oid,'UPDATE') IS DISTINCT FROM
            (n.nspname::text||'.'||c.relname::text=ANY($3::text[])))
          OR (pg_catalog.has_any_column_privilege(r.oid,c.oid,'SELECT') AND
            NOT n.nspname::text||'.'||c.relname::text=ANY($2::text[]))
          OR (pg_catalog.has_any_column_privilege(r.oid,c.oid,'UPDATE') AND
            NOT n.nspname::text||'.'||c.relname::text=ANY($3::text[])) END)
        AND (SELECT count(*) FROM pg_catalog.pg_namespace n CROSS JOIN LATERAL pg_catalog.aclexplode(n.nspacl) a
          WHERE a.grantee=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=$1))=1
        AND EXISTS(SELECT 1 FROM pg_catalog.pg_namespace n CROSS JOIN LATERAL pg_catalog.aclexplode(n.nspacl) a
          WHERE n.nspname='public' AND a.grantee=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=$1)
            AND a.grantor=n.nspowner AND a.privilege_type='USAGE' AND NOT a.is_grantable)
        AND NOT EXISTS(SELECT 1 FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
          WHERE n.nspname<>'information_schema' AND pg_catalog.left(n.nspname::text,3)<>'pg_'
            AND p.proowner<>(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=$1)
            AND pg_catalog.has_function_privilege((SELECT oid FROM pg_catalog.pg_roles WHERE rolname=$1),p.oid,'EXECUTE'))
      """,
      [
        role,
        for({r, "SELECT"} <- contract.grants, do: r),
        for({r, "UPDATE"} <- contract.grants, do: r)
      ]
    )

    safe!(
      repo,
      deadline,
      backend,
      """
      SELECT count(*)=12 AND bool_and(c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=$2)
        AND c.relkind='r' AND c.relrowsecurity=(c.relname<>'mixer_builds')
        AND c.relforcerowsecurity=(c.relname<>'mixer_builds'))
      FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
      WHERE n.nspname::text||'.'||c.relname::text=ANY($1::text[])
      """,
      [Enum.uniq(relations), owner]
    )

    policies =
      Enum.map(
        contract.policies,
        &Map.merge(&1, %{role: role, expression: contract.policy_expression})
      ) ++
        Enum.map(
          contract.old_policies,
          &Map.merge(&1, %{role: "PUBLIC", expression: contract.old_policy_expression})
        )

    for policy <- policies do
      safe!(
        repo,
        deadline,
        backend,
        """
        SELECT count(*)=1 AND bool_and(p.polpermissive AND p.polcmd::text=$2
          AND p.polroles=CASE WHEN $3::text='PUBLIC' THEN ARRAY[0::oid]
            ELSE ARRAY[(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=$3)] END
          AND pg_catalog.pg_get_expr(p.polqual,p.polrelid)=$4
          AND pg_catalog.pg_get_expr(p.polwithcheck,p.polrelid) IS NOT DISTINCT FROM $5::text)
        FROM pg_catalog.pg_policy p WHERE p.polrelid='public.mixer_authz_applications'::regclass AND p.polname=$1
        """,
        [policy.name, policy.command, policy.role, policy.expression, policy.check]
      )
    end

    safe!(
      repo,
      deadline,
      backend,
      """
      SELECT (SELECT count(*) FROM pg_catalog.pg_policy
          WHERE polrelid='public.mixer_authz_applications'::regclass)=4
        AND NOT EXISTS(SELECT 1 FROM pg_catalog.pg_policy p WHERE
        (SELECT oid FROM pg_catalog.pg_roles WHERE rolname=$1)=ANY(p.polroles)
        AND NOT(p.polrelid='public.mixer_authz_applications'::regclass AND p.polname=ANY($2::text[])))
      """,
      [role, Enum.map(contract.policies, & &1.name)]
    )

    :ok
  rescue
    error ->
      readiness_probe(:build_catalog_rescue, error.__struct__, __STACKTRACE__)
      raise Unavailable
  catch
    kind, _ ->
      readiness_probe(:build_catalog_catch, kind, __STACKTRACE__)
      raise Unavailable
  end

  defp safe!(repo, deadline, backend, sql, params) do
    result = query!(repo, deadline, "SELECT pg_catalog.pg_backend_pid(), (" <> sql <> ")", params)
    true = result.connection_id === backend
    [[^backend, true]] = result.rows
    :ok
  end

  defp query!(repo, deadline, sql, params) do
    remaining = deadline - System.monotonic_time(:millisecond)
    true = remaining > 0 and remaining <= 5000

    result =
      Ecto.Adapters.SQL.query!(repo, sql, params, timeout: remaining, queue: false, log: false)

    true = System.monotonic_time(:millisecond) < deadline
    %Postgrex.Result{command: :select, num_rows: 1, messages: []} = result
    result
  end

  # R1478 diagnostic only; helper exists only in test/support and activates for one exact module.
  defp readiness_probe(stage, class, stack) do
    if Code.ensure_loaded?(MixerHosted.Test.OrdinaryReadinessFrontier),
      do: apply(MixerHosted.Test.OrdinaryReadinessFrontier, :record, [stage, class, stack])
    :ok
  rescue
    _ -> :ok
  catch
    _, _ -> :ok
  end
end
