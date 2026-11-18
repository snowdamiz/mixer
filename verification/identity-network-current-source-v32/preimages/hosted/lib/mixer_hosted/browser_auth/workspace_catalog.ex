defmodule MixerHosted.BrowserAuth.WorkspaceCatalog do
  @moduledoc false
  alias MixerHosted.BrowserAuth.RelationCatalog.Unavailable
  alias MixerHosted.CustomerWorkspace.SelfServiceSchema, as: Schema

  @name "mixer_workspace_self_service_v1"
  @principal "public.mixer_authz_principals"
  @member "((id = current_setting('mixer.workspace.member_id'::text, true)) AND (identity_class = 'human'::text))"
  @settings [
    "search_path=pg_catalog",
    "statement_timeout=5s",
    "lock_timeout=500ms",
    "idle_in_transaction_session_timeout=5s"
  ]

  # PostgreSQL 17 policy deparse from the reviewed authorization and discovery migrations.
  @tenant_policy_digest "072102acd3d6c69fea13fc5ce8f77b6828ccd223cc1d415725113d4838836cb9"

  def protected_rows(writer, owner) do
    grants =
      grants()
      |> Enum.filter(fn {relation, _, _} -> relation in identity_relations() end)
      |> Enum.map(fn {relation, column, privilege} ->
        %{
          "relation" => relation,
          "column" => column,
          "null" => false,
          "grantee" => writer,
          "grantor" => owner,
          "privilege" => privilege,
          "option" => false
        }
      end)

    policies =
      for {name, command, check} <- [
            {"workspace_member_read", "r", nil},
            {"workspace_member_lock", "w", "false"}
          ] do
        %{
          "relation" => @principal,
          "name" => name,
          "command" => command,
          "permissive" => true,
          "roles" => [writer],
          "using" => @member,
          "check" => check
        }
      end

    {grants, policies}
  end

  def check!(repo, roles, deadline, backend) do
    writer = Schema.writer()
    if writer in Map.values(roles), do: raise(Unavailable)
    context = {repo, deadline, backend}

    [[oid]] =
      query!(
        context,
        """
        SELECT r.oid::bigint FROM pg_catalog.pg_roles r
        WHERE r.rolname=$1 AND NOT (r.rolcanlogin OR r.rolsuper OR r.rolbypassrls OR r.rolinherit
          OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication)
          AND r.rolvaliduntil IS NULL AND r.rolconnlimit=-1 AND r.rolconfig IS NULL
          AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_db_role_setting s WHERE s.setrole=r.oid)
          AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_auth_members m WHERE r.oid IN (m.member,m.roleid))
          AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_database d
            WHERE d.datdba=r.oid OR pg_catalog.has_database_privilege(r.oid,d.oid,'CREATE'))
          AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_namespace n
            WHERE n.nspowner=r.oid OR pg_catalog.has_schema_privilege(r.oid,n.oid,'CREATE'))
          AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_class c WHERE c.relowner=r.oid)
          AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_type t WHERE t.typowner=r.oid)
          AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_default_acl d
            CROSS JOIN LATERAL pg_catalog.aclexplode(d.defaclacl) a
            WHERE d.defaclrole=r.oid OR a.grantee=r.oid)
        """,
        [writer]
      )

    function!(context, oid, roles)
    build_count!(context, oid, roles)
    grants!(context, oid, roles.relation_owner)
    policies!(context, oid, roles.relation_owner)
    tenant_policies!(context, oid)
    oid
  end

  defp function!(context, writer, roles) do
    [[true]] =
      query!(
        context,
        """
        SELECT count(*)=1 AND bool_and(n.nspname='public' AND p.proname=$1
          AND p.proowner=$2::oid AND l.lanname='plpgsql' AND CASE WHEN pg_catalog.octet_length(p.prosrc)<=65536 THEN p.prosrc=$3 ELSE false END AND p.proconfig=$4::text[]
          AND p.proargtypes='25 25 25 3802 20 20'::oidvector AND p.pronargs=6
          AND p.proargnames=ARRAY['op','org','target','body','issued','expires']::text[]
          AND p.prorettype='pg_catalog.jsonb'::regtype AND p.prokind='f' AND p.prosecdef
          AND p.provolatile='v' AND p.proparallel='u' AND NOT (p.proretset OR p.proisstrict OR p.proleakproof)
          AND p.pronargdefaults=0 AND p.proargdefaults IS NULL AND p.proargmodes IS NULL
          AND p.proallargtypes IS NULL AND p.provariadic=0 AND p.prosupport=0 AND p.probin IS NULL
          AND p.prosqlbody IS NULL AND p.procost=100 AND p.prorows=0
          AND pg_catalog.has_function_privilege($5::text,p.oid,'EXECUTE')
          AND NOT pg_catalog.has_function_privilege($6::text,p.oid,'EXECUTE')
          AND NOT pg_catalog.has_function_privilege($7::text,p.oid,'EXECUTE')
          AND (SELECT count(*) FROM pg_catalog.aclexplode(p.proacl) a
               WHERE a.grantee IN (p.proowner,(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=$5))
                 AND a.grantor=p.proowner AND a.privilege_type='EXECUTE' AND NOT a.is_grantable)=2
          AND (SELECT count(*) FROM pg_catalog.aclexplode(p.proacl))=2)
        FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
        JOIN pg_catalog.pg_language l ON l.oid=p.prolang
        WHERE p.proowner=$2::oid OR (n.nspname='public' AND p.proname=$1)
        """,
        [
          @name,
          writer,
          Schema.body(),
          @settings,
          roles.ordinary_runtime_login,
          roles.lifecycle_login,
          roles.writer
        ]
      )

    [[true]] =
      query!(
        context,
        """
        SELECT NOT EXISTS(SELECT 1 FROM pg_catalog.pg_proc p
          JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
          WHERE p.proowner<>$1::oid AND n.nspname NOT IN ('pg_catalog','information_schema')
            AND p.prosecdef AND pg_catalog.has_function_privilege($1::oid,p.oid,'EXECUTE')
            AND NOT (n.nspname='public' AND p.proname='mixer_workspace_build_count_v1'))
          AND (SELECT count(*) FROM pg_catalog.pg_namespace n
            CROSS JOIN LATERAL pg_catalog.aclexplode(n.nspacl) a WHERE a.grantee=$1::oid)=1
          AND EXISTS (SELECT 1 FROM pg_catalog.pg_namespace n
            CROSS JOIN LATERAL pg_catalog.aclexplode(n.nspacl) a WHERE a.grantee=$1::oid
            AND n.nspname='public' AND a.grantor=n.nspowner AND a.privilege_type='USAGE' AND NOT a.is_grantable)
        """,
        [writer]
      )
  end

  defp build_count!(context, writer, roles) do
    [[true]] =
      query!(
        context,
        """
        SELECT count(*)=1 AND bool_and(o.rolname=$2
          AND p.prosrc=$3 AND p.proconfig=ARRAY['search_path=pg_catalog']::text[]
          AND p.proargtypes='25'::oidvector AND p.pronargs=1 AND p.proargnames=ARRAY['target']::text[]
          AND p.prorettype='pg_catalog.int8'::regtype AND p.prokind='f' AND p.prosecdef
          AND p.provolatile='v' AND p.proparallel='u' AND NOT (p.proretset OR p.proisstrict OR p.proleakproof)
          AND p.pronargdefaults=0 AND p.proargdefaults IS NULL AND p.proargmodes IS NULL
          AND p.proallargtypes IS NULL AND p.provariadic=0 AND p.prosupport=0 AND p.probin IS NULL
          AND p.prosqlbody IS NULL AND p.procost=100 AND p.prorows=0 AND l.lanname='sql'
          AND (SELECT count(*) FROM pg_catalog.aclexplode(p.proacl) a
               WHERE a.grantee IN (p.proowner,$1::oid) AND a.grantor=p.proowner
                 AND a.privilege_type='EXECUTE' AND NOT a.is_grantable)=2
          AND (SELECT count(*) FROM pg_catalog.aclexplode(p.proacl))=2
          AND c.relowner=p.proowner AND c.relkind='r'
          AND (NOT c.relforcerowsecurity OR (
            EXISTS (SELECT 1 FROM pg_catalog.pg_policy q WHERE q.polrelid=c.oid
              AND q.polpermissive AND q.polcmd='*' AND q.polroles=ARRAY[p.proowner]
              AND pg_catalog.pg_get_expr(q.polqual,q.polrelid)='true'
              AND pg_catalog.pg_get_expr(q.polwithcheck,q.polrelid)='true')
            AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_policy q WHERE q.polrelid=c.oid
              AND NOT q.polpermissive AND q.polroles && ARRAY[0::oid,p.proowner]))))
        FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
        JOIN pg_catalog.pg_language l ON l.oid=p.prolang
        JOIN pg_catalog.pg_roles o ON o.oid=p.proowner
        JOIN pg_catalog.pg_class c ON c.oid='public.mixer_builds'::pg_catalog.regclass
        WHERE n.nspname='public' AND p.proname='mixer_workspace_build_count_v1'
        """,
        [writer, roles.relation_owner, Schema.build_count_body()]
      )
  end

  defp grants!(context, writer, owner) do
    grants = grants()

    [[true]] =
      query!(
        context,
        """
        WITH expected AS (
          SELECT g.relation,g.col,g.privilege,$1::oid AS grantee,r.oid AS grantor,false AS grantable
          FROM ROWS FROM (pg_catalog.unnest($2::text[]),pg_catalog.unnest($3::text[]),pg_catalog.unnest($4::text[])) g(relation,col,privilege)
          CROSS JOIN pg_catalog.pg_roles r WHERE r.rolname=$5
        ), actual AS (
          SELECT n.nspname::text||'.'||c.relname::text AS relation,a.col,
            a.privilege_type AS privilege,a.grantee,a.grantor,a.is_grantable AS grantable
          FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
          CROSS JOIN LATERAL (
            SELECT NULL::text AS col, q.* FROM pg_catalog.aclexplode(c.relacl) q
            UNION ALL SELECT b.attname::text,q.* FROM pg_catalog.pg_attribute b
              CROSS JOIN LATERAL pg_catalog.aclexplode(b.attacl) q WHERE b.attrelid=c.oid
          ) a WHERE a.grantee=$1::oid OR
            (a.grantee=0 AND n.nspname::text||'.'||c.relname::text=ANY($2::text[]))
        )
        SELECT NOT EXISTS ((TABLE expected EXCEPT ALL TABLE actual) UNION ALL (TABLE actual EXCEPT ALL TABLE expected))
          AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname<>'information_schema' AND pg_catalog.left(n.nspname::text,3)<>'pg_' AND
              CASE WHEN c.relkind='S' THEN pg_catalog.has_sequence_privilege($1::oid,c.oid,'SELECT,UPDATE,USAGE')
              WHEN c.relkind IN ('r','p','v','m','f') THEN
                pg_catalog.has_table_privilege($1::oid,c.oid,'DELETE,UPDATE,TRUNCATE,REFERENCES,TRIGGER,MAINTAIN')
                OR pg_catalog.has_any_column_privilege($1::oid,c.oid,'REFERENCES')
                OR (pg_catalog.has_any_column_privilege($1::oid,c.oid,'SELECT')
                  IS DISTINCT FROM (n.nspname::text||'.'||c.relname::text=ANY($6::text[])))
                OR (pg_catalog.has_table_privilege($1::oid,c.oid,'INSERT')
                  IS DISTINCT FROM (n.nspname::text||'.'||c.relname::text=ANY($7::text[])))
                OR (pg_catalog.has_any_column_privilege($1::oid,c.oid,'UPDATE')
                  IS DISTINCT FROM (n.nspname::text||'.'||c.relname::text=ANY($8::text[])))
                OR (n.nspname::text||'.'||c.relname::text=ANY($8::text[]) AND EXISTS (
                  SELECT 1 FROM pg_catalog.pg_attribute b WHERE b.attrelid=c.oid
                    AND b.attnum>0 AND NOT b.attisdropped
                    AND pg_catalog.has_column_privilege($1::oid,c.oid,b.attnum,'UPDATE')
                      IS DISTINCT FROM EXISTS (
                        SELECT 1 FROM expected e WHERE e.relation=n.nspname::text||'.'||c.relname::text
                          AND e.col=b.attname::text AND e.privilege='UPDATE')))
                OR (pg_catalog.has_any_column_privilege($1::oid,c.oid,'INSERT')
                  IS DISTINCT FROM (n.nspname::text||'.'||c.relname::text=ANY($7::text[])))
              ELSE false END)
        """,
        [
          writer,
          Enum.map(grants, &elem(&1, 0)),
          Enum.map(grants, &elem(&1, 1)),
          Enum.map(grants, &elem(&1, 2)),
          owner,
          for({rel, _, "SELECT"} <- grants, do: rel),
          for({rel, _, "INSERT"} <- grants, do: rel),
          for({rel, _, "UPDATE"} <- grants, do: rel)
        ]
      )
  end

  defp policies!(context, writer, owner) do
    rows =
      query!(
        context,
        """
        SELECT c.relname::text,p.polname::text,p.polcmd::text,p.polpermissive,p.polroles,
          CASE WHEN pg_catalog.octet_length(p.polqual::text) < 8192 THEN pg_catalog.pg_get_expr(p.polqual,p.polrelid) END,
          CASE WHEN pg_catalog.octet_length(p.polwithcheck::text) < 8192 THEN pg_catalog.pg_get_expr(p.polwithcheck,p.polrelid) END,
          n.nspname='public' AND c.relkind='r' AND c.relrowsecurity AND c.relforcerowsecurity
            AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=$2)
        FROM pg_catalog.pg_policy p JOIN pg_catalog.pg_class c ON c.oid=p.polrelid
        JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
        WHERE $1::oid=ANY(p.polroles)
        LIMIT 8
        """,
        [writer, owner]
      )

    expected =
      for table <- Schema.tenant_tables() do
        column = if table == "organizations", do: "id", else: "organization_id"
        predicate = "(#{column} = current_setting('mixer.authz.organization_id'::text, true))"

        [
          "mixer_authz_" <> table,
          "workspace_self_service",
          "*",
          true,
          [writer],
          predicate,
          predicate,
          true
        ]
      end

    expected =
      expected ++
        [
          [
            "mixer_authz_principals",
            "workspace_member_read",
            "r",
            true,
            [writer],
            @member,
            nil,
            true
          ],
          [
            "mixer_authz_principals",
            "workspace_member_lock",
            "w",
            true,
            [writer],
            @member,
            "false",
            true
          ]
        ]

    true = Enum.frequencies(rows) === Enum.frequencies(expected)
  end

  defp tenant_policies!(context, writer) do
    [[@tenant_policy_digest]] =
      query!(
        context,
        """
        WITH policies AS (
          SELECT c.relname::text AS relation, p.polname::text AS name,
            pg_catalog.jsonb_build_array(c.relname::text,p.polname::text,p.polcmd::text,p.polpermissive,
              p.polroles,
              CASE WHEN pg_catalog.octet_length(p.polqual::text)<=65536
                THEN pg_catalog.pg_get_expr(p.polqual,p.polrelid)
                WHEN p.polqual IS NOT NULL THEN 'policy expression oversized' END,
              CASE WHEN pg_catalog.octet_length(p.polwithcheck::text)<=65536
                THEN pg_catalog.pg_get_expr(p.polwithcheck,p.polrelid)
                WHEN p.polwithcheck IS NOT NULL THEN 'policy expression oversized' END) AS row
          FROM pg_catalog.pg_policy p JOIN pg_catalog.pg_class c ON c.oid=p.polrelid
          JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
          WHERE n.nspname='public' AND c.relname::text=ANY($2::text[]) AND NOT $1::oid=ANY(p.polroles)
          LIMIT 14
        )
        SELECT CASE WHEN count(*)=13 THEN pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to(
          pg_catalog.jsonb_agg(row ORDER BY relation COLLATE "C",name COLLATE "C")::text,'UTF8')),'hex')
        END FROM policies
        """,
        [writer, Enum.map(Schema.tenant_tables(), &("mixer_authz_" <> &1))]
      )
  end

  defp identity_relations, do: authz_relations(Schema.identity_tables())
  defp authz_relations(tables), do: Enum.map(tables, &("public.mixer_authz_" <> &1))

  defp grants do
    tenant = authz_relations(Schema.tenant_tables())
    build_create = Enum.map(Schema.build_create_tables(), &("public." <> &1))
    build_read = Enum.map(Schema.build_read_tables(), &("public." <> &1))

    reads =
      Enum.map(tenant ++ identity_relations() ++ build_create ++ build_read, &{&1, nil, "SELECT"})

    inserts = Enum.map(tenant ++ build_create, &{&1, nil, "INSERT"})

    updates =
      for {table, columns} <- Schema.tenant_update_columns(),
          column <- columns,
          do: {"public.mixer_authz_" <> table, column, "UPDATE"}

    reads ++ inserts ++ updates ++ [{@principal, "revision", "UPDATE"}]
  end

  defp query!({repo, deadline, backend}, sql, params) do
    remaining = deadline - System.monotonic_time(:millisecond)
    true = remaining in 1..5000

    %Postgrex.Result{command: :select, connection_id: ^backend, rows: rows, messages: []} =
      Ecto.Adapters.SQL.query!(repo, sql, params, timeout: remaining, queue: false, log: false)

    rows
  end
end
