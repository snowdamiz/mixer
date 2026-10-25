defmodule MixerHosted.BrowserAuth.Catalog do
  @moduledoc """
  Internal function/type capability prerequisite for the future lifecycle owner.

  This has no application caller and cannot authorize storage readiness. It does
  not implement the required relation, policy, constraint, index or trigger
  admission. The trusted adapter must supply its own transaction Repo, the exact
  validated RuntimeConfig expected_roles and the original monotonic deadline.
  `in_transaction?/0` proves connection checkout, not Store ownership/provenance.
  Neither the Repo nor these expectations may come from a request.
  """
  alias MixerHosted.BrowserAuth.CatalogManifest

  defmodule Unavailable do
    @moduledoc false
    defexception message: "browser catalog function surface unavailable"
  end

  @role_keys [:lifecycle_login, :writer, :relation_owner, :ordinary_runtime_login]
  @query_limit_ms 5_000
  @catalog_row_limit 4_096

  @doc false
  def check_function_surface!(repo, expected_roles, monotonic_deadline_ms) do
    try do
      validate_roles!(expected_roles)
      require!(is_atom(repo) and repo.in_transaction?())
      now = System.monotonic_time(:millisecond)
      require!(is_integer(monotonic_deadline_ms))
      require!(monotonic_deadline_ms > now and monotonic_deadline_ms <= now + @query_limit_ms)
      context = {repo, monotonic_deadline_ms}
      session!(context, expected_roles)
      roles!(context, expected_roles)
      functions!(context, expected_roles)
      composites!(context, expected_roles)
      escape_paths!(context, expected_roles)
      remaining!(monotonic_deadline_ms)
      :function_surface_verified
    rescue
      _ -> raise Unavailable
    catch
      _, _ -> raise Unavailable
    end
  end

  defp validate_roles!(roles) do
    require!(is_map(roles) and Enum.sort(Map.keys(roles)) == Enum.sort(@role_keys))
    names = Map.values(roles)
    require!(Enum.all?(names, &role_name?/1) and length(Enum.uniq(names)) == 4)
  end

  defp role_name?(name) when is_binary(name) and byte_size(name) in 1..63 do
    name != "public" and not String.starts_with?(name, "pg_") and
      name
      |> :binary.bin_to_list()
      |> Enum.with_index()
      |> Enum.all?(fn {c, i} -> c in ?a..?z or c == ?_ or (i > 0 and c in ?0..?9) end)
  end

  defp role_name?(_), do: false

  defp session!(context, roles) do
    require!(
      query!(context, """
      SELECT current_user::pg_catalog.text,session_user::pg_catalog.text,
        pg_catalog.current_setting('transaction_isolation'),
        pg_catalog.current_setting('statement_timeout'),
        pg_catalog.current_setting('lock_timeout'),
        pg_catalog.current_setting('idle_in_transaction_session_timeout'),
        pg_catalog.current_setting('jit'),pg_catalog.current_setting('search_path'),
        pg_catalog.current_setting('bytea_output')
      WHERE pg_catalog.octet_length(pg_catalog.current_setting('search_path'))<=64
      """) == [
        [
          roles.lifecycle_login,
          roles.lifecycle_login,
          "read committed",
          "5s",
          "500ms",
          "5s",
          "off",
          "pg_catalog",
          "hex"
        ]
      ]
    )
  end

  defp roles!(context, roles) do
    rows =
      query!(context, """
      SELECT r.oid::pg_catalog.int8,r.rolname::pg_catalog.text,r.rolcanlogin,
        r.rolinherit,r.rolsuper,r.rolbypassrls,r.rolcreaterole,r.rolcreatedb,r.rolreplication
      FROM pg_catalog.pg_roles r
      LIMIT 4097
      """)

    by_name =
      Map.new(rows, fn row ->
        remaining!(elem(context, 1))
        {Enum.at(row, 1), row}
      end)

    for key <- @role_keys do
      remaining!(elem(context, 1))
      expected_login = key in [:lifecycle_login, :ordinary_runtime_login]
      [_oid, _name | flags] = Map.fetch!(by_name, Map.fetch!(roles, key))
      require!(flags == [expected_login, false, false, false, false, false, false])
    end

    edges =
      query!(context, """
      SELECT member::pg_catalog.int8,roleid::pg_catalog.int8
      FROM pg_catalog.pg_auth_members
      LIMIT 4097
      """)

    lifecycle_oid = hd(Map.fetch!(by_name, roles.lifecycle_login))
    writer_oid = hd(Map.fetch!(by_name, roles.writer))
    owner_oid = hd(Map.fetch!(by_name, roles.relation_owner))
    ordinary_oid = hd(Map.fetch!(by_name, roles.ordinary_runtime_login))
    isolated = [lifecycle_oid, writer_oid]

    require!(
      Enum.all?(edges, fn [member, role] ->
        remaining!(elem(context, 1))
        member not in isolated and role not in isolated
      end)
    )

    reachable = reachable(MapSet.new([ordinary_oid]), edges, elem(context, 1))

    require!(
      not Enum.any?([lifecycle_oid, writer_oid, owner_oid], &MapSet.member?(reachable, &1))
    )

    privilege_reachable =
      MapSet.union(
        reachable,
        reachable(MapSet.new([owner_oid]), edges, elem(context, 1))
      )

    for [oid, name, _login, _inherit, super, bypass, create_role, create_db, replication] <- rows,
        MapSet.member?(privilege_reachable, oid) do
      remaining!(elem(context, 1))
      require!(not String.starts_with?(name, "pg_"))
      require!(not (super or bypass or create_role or create_db or replication))
    end

    # Ownership is an authority route even without an explicit ACL grant. The
    # writer may own only functions; the relation owner is intentionally allowed
    # to own the accepted installation and is checked for restricted flags above.
    owned =
      query!(context, """
      SELECT owner::pg_catalog.int8 FROM (
        SELECT relowner AS owner FROM pg_catalog.pg_class
        UNION SELECT nspowner FROM pg_catalog.pg_namespace
        UNION SELECT datdba FROM pg_catalog.pg_database
      ) owners
      LIMIT 4097
      """)

    require!(
      Enum.all?(owned, fn [oid] ->
        remaining!(elem(context, 1))
        oid not in isolated and not MapSet.member?(reachable, oid)
      end)
    )

    # A reachable role may itself own a function and make it SECURITY DEFINER.
    function_owners =
      query!(
        context,
        "SELECT DISTINCT proowner::pg_catalog.int8 FROM pg_catalog.pg_proc LIMIT 4097"
      )

    require!(
      Enum.all?(function_owners, fn [oid] ->
        remaining!(elem(context, 1))
        not MapSet.member?(reachable, oid)
      end)
    )

    require!(
      query!(
        context,
        """
        SELECT 1 FROM pg_catalog.pg_namespace n
        WHERE pg_catalog.has_schema_privilege($1::pg_catalog.text,n.oid,'CREATE')
           OR pg_catalog.has_schema_privilege($2::pg_catalog.text,n.oid,'CREATE')
           OR pg_catalog.has_schema_privilege($3::pg_catalog.text,n.oid,'CREATE')
        LIMIT 1
        """,
        [roles.lifecycle_login, roles.writer, roles.ordinary_runtime_login]
      ) == []
    )

    require!(
      query!(
        context,
        """
        SELECT pg_catalog.has_schema_privilege($1::pg_catalog.text,n.oid,'USAGE'),
          pg_catalog.has_schema_privilege($2::pg_catalog.text,n.oid,'USAGE')
        FROM pg_catalog.pg_namespace n WHERE n.nspname='public'
        """,
        [roles.lifecycle_login, roles.writer]
      ) == [[true, true]]
    )

    require!(
      query!(
        context,
        """
        SELECT 1 FROM pg_catalog.pg_database d WHERE d.datname=pg_catalog.current_database()
          AND (pg_catalog.has_database_privilege($1::pg_catalog.text,d.oid,'CREATE')
            OR pg_catalog.has_database_privilege($2::pg_catalog.text,d.oid,'CREATE')
            OR pg_catalog.has_database_privilege($3::pg_catalog.text,d.oid,'CREATE'))
        """,
        [roles.lifecycle_login, roles.writer, roles.ordinary_runtime_login]
      ) == []
    )
  end

  defp reachable(found, edges, deadline) do
    remaining!(deadline)

    expanded =
      Enum.reduce(edges, found, fn [member, role], acc ->
        remaining!(deadline)
        if MapSet.member?(found, member), do: MapSet.put(acc, role), else: acc
      end)

    if MapSet.equal?(found, expanded), do: found, else: reachable(expanded, edges, deadline)
  end

  defp functions!(context, roles) do
    rows =
      query!(
        context,
        """
        SELECT n.nspname::pg_catalog.text,p.proname::pg_catalog.text,p.oid::pg_catalog.int8,
          CASE WHEN p.pronargs<=16 AND pg_catalog.octet_length(pg_catalog.oidvectortypes(p.proargtypes))<=4096
            THEN pg_catalog.oidvectortypes(p.proargtypes) END,
          CASE WHEN pg_catalog.octet_length(pg_catalog.pg_get_function_result(p.oid))<=1024
            THEN pg_catalog.pg_get_function_result(p.oid) END,
          l.lanname::pg_catalog.text,o.rolname::pg_catalog.text,
          CASE WHEN pg_catalog.octet_length(p.prosrc)<=65536 THEN p.prosrc END,
          CASE WHEN pg_catalog.cardinality(p.proconfig)=5
            AND pg_catalog.octet_length(p.proconfig::pg_catalog.text)<=512 THEN p.proconfig END,
          p.prosecdef,p.prokind::pg_catalog.text,p.provolatile::pg_catalog.text,
          p.proisstrict,p.proleakproof,p.proparallel::pg_catalog.text,p.proretset,
          p.provariadic::pg_catalog.int8,p.pronargdefaults,
          CASE WHEN p.proargmodes IS NULL THEN NULL ELSE 'present' END,
          p.prosupport::pg_catalog.oid::pg_catalog.int8,
          CASE WHEN p.probin IS NULL THEN NULL ELSE 'present' END,p.prosqlbody IS NULL,
          CASE WHEN p.proargnames IS NULL THEN NULL
            WHEN pg_catalog.cardinality(p.proargnames)<=16
              AND pg_catalog.octet_length(p.proargnames::pg_catalog.text)<=1024 THEN p.proargnames
            ELSE ARRAY['__oversized__']::pg_catalog.text[] END,
          pg_catalog.has_function_privilege($1::pg_catalog.text,p.oid,'EXECUTE'),
          pg_catalog.has_function_privilege($2::pg_catalog.text,p.oid,'EXECUTE'),
          pg_catalog.has_function_privilege($3::pg_catalog.text,p.oid,'EXECUTE')
        FROM pg_catalog.pg_proc p
        JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
        JOIN pg_catalog.pg_language l ON l.oid=p.prolang
        JOIN pg_catalog.pg_roles o ON o.oid=p.proowner
        WHERE pg_catalog.left(p.proname::pg_catalog.text,14)='mixer_browser_'
        ORDER BY n.nspname,p.proname,p.oid
        LIMIT 19
        """,
        [roles.lifecycle_login, roles.writer, roles.ordinary_runtime_login]
      )

    require!(length(rows) == 18)

    require!(
      MapSet.new(Enum.map(rows, &Enum.at(&1, 1))) ==
        MapSet.new(Map.keys(CatalogManifest.functions()))
    )

    for [
          schema,
          name,
          _oid,
          args,
          result,
          language,
          owner,
          source,
          settings,
          security_definer,
          kind,
          volatility,
          strict,
          leakproof,
          parallel,
          setof,
          variadic,
          defaults,
          modes,
          support,
          binary,
          no_sql_body,
          argument_names,
          lifecycle,
          writer,
          ordinary
        ] <- rows do
      remaining!(elem(context, 1))
      expected = Map.fetch!(CatalogManifest.functions(), name)
      require!(schema == "public" and language == "plpgsql" and owner == roles.writer)
      require!(args == String.replace(expected.signature, ",", ", "))
      require!(result == Map.fetch!(CatalogManifest.returns(), name))
      require!(source == expected.source and is_list(settings))
      require!(Enum.sort(settings) == Enum.sort(expected.settings))

      require!(
        [security_definer, kind, volatility, strict, leakproof, parallel, setof] ==
          [true, "f", "v", false, false, "u", false]
      )

      require!(
        [variadic, defaults, modes, support, binary, no_sql_body] == [0, 0, nil, 0, nil, true]
      )

      require!(argument_names == Map.fetch!(CatalogManifest.argument_names(), name))
      require!(lifecycle == expected.runtime_execute and writer and not ordinary)
    end

    acls =
      query!(context, """
      SELECT p.proname::pg_catalog.text,
        CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE g.rolname::pg_catalog.text END,
        a.privilege_type,a.is_grantable
      FROM pg_catalog.pg_proc p
      JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
      CROSS JOIN LATERAL pg_catalog.aclexplode(
        COALESCE(p.proacl,pg_catalog.acldefault('f',p.proowner))) a
      LEFT JOIN pg_catalog.pg_roles g ON g.oid=a.grantee
      WHERE n.nspname='public' AND pg_catalog.left(p.proname::pg_catalog.text,14)='mixer_browser_'
      LIMIT 28
      """)

    expected_acls =
      Enum.flat_map(CatalogManifest.functions(), fn {name, expected} ->
        [[name, roles.writer, "EXECUTE", false]] ++
          if expected.runtime_execute,
            do: [[name, roles.lifecycle_login, "EXECUTE", false]],
            else: []
      end)

    require!(Enum.sort(acls) == Enum.sort(expected_acls))
  end

  defp composites!(context, roles) do
    rows =
      query!(
        context,
        """
        SELECT t.typname::pg_catalog.text,t.typtype::pg_catalog.text,
          o.rolname::pg_catalog.text,c.relkind::pg_catalog.text,
          pg_catalog.has_type_privilege($1::pg_catalog.text,t.oid,'USAGE'),
          pg_catalog.has_type_privilege($2::pg_catalog.text,t.oid,'USAGE'),
          pg_catalog.has_type_privilege($3::pg_catalog.text,t.oid,'USAGE')
        FROM pg_catalog.pg_type t
        JOIN pg_catalog.pg_namespace n ON n.oid=t.typnamespace
        JOIN pg_catalog.pg_roles o ON o.oid=t.typowner
        JOIN pg_catalog.pg_class c ON c.oid=t.typrelid
        WHERE n.nspname='public' AND t.typname=ANY($4::pg_catalog.text[])
        LIMIT 4
        """,
        [
          roles.lifecycle_login,
          roles.writer,
          roles.ordinary_runtime_login,
          Map.keys(CatalogManifest.composites())
        ]
      )

    require!(length(rows) == 3)

    for [_name, kind, owner, relation_kind, lifecycle, writer, ordinary] <- rows do
      remaining!(elem(context, 1))

      require!(
        [kind, owner, relation_kind, lifecycle, writer, ordinary] ==
          ["c", roles.relation_owner, "c", true, true, false]
      )
    end

    fields =
      query!(
        context,
        """
        SELECT t.typname::pg_catalog.text,a.attname::pg_catalog.text,
          pg_catalog.format_type(a.atttypid,a.atttypmod),a.attnum::pg_catalog.int4,
          a.attisdropped,a.attnotnull,a.atthasdef,a.attgenerated::pg_catalog.text,
          a.attidentity::pg_catalog.text,a.attcollation=ft.typcollation,a.attndims::pg_catalog.int4
        FROM pg_catalog.pg_type t
        JOIN pg_catalog.pg_namespace n ON n.oid=t.typnamespace
        JOIN pg_catalog.pg_attribute a ON a.attrelid=t.typrelid AND a.attnum>0
        LEFT JOIN pg_catalog.pg_type ft ON ft.oid=a.atttypid
        WHERE n.nspname='public' AND t.typname=ANY($1::pg_catalog.text[])
        ORDER BY t.typname,a.attnum
        LIMIT 26
        """,
        [Map.keys(CatalogManifest.composites())]
      )

    expected_fields =
      for {type, fields} <- CatalogManifest.composites(),
          {{name, kind}, index} <- Enum.with_index(fields, 1),
          do: [
            type,
            name,
            kind,
            index,
            false,
            false,
            false,
            "",
            "",
            true,
            if(String.ends_with?(kind, "[]"), do: 1, else: 0)
          ]

    require!(Enum.sort(fields) == Enum.sort(expected_fields))

    acls =
      query!(
        context,
        """
        SELECT t.typname::pg_catalog.text,
          CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE g.rolname::pg_catalog.text END,
          a.privilege_type,a.is_grantable
        FROM pg_catalog.pg_type t
        JOIN pg_catalog.pg_namespace n ON n.oid=t.typnamespace
        CROSS JOIN LATERAL pg_catalog.aclexplode(
          COALESCE(t.typacl,pg_catalog.acldefault('T',t.typowner))) a
        LEFT JOIN pg_catalog.pg_roles g ON g.oid=a.grantee
        WHERE n.nspname='public' AND t.typname=ANY($1::pg_catalog.text[])
        LIMIT 10
        """,
        [Map.keys(CatalogManifest.composites())]
      )

    expected_acls =
      for type <- Map.keys(CatalogManifest.composites()),
          role <- [roles.relation_owner, roles.writer, roles.lifecycle_login],
          do: [type, role, "USAGE", false]

    require!(Enum.sort(acls) == Enum.sort(expected_acls))
  end

  defp escape_paths!(context, roles) do
    # Reject every callable application SECURITY DEFINER outside the exact
    # reviewed surface, including a helper in a second accessible schema.
    rows =
      query!(
        context,
        """
        SELECT n.nspname::pg_catalog.text,p.proname::pg_catalog.text,
          pg_catalog.has_function_privilege($1::pg_catalog.text,p.oid,'EXECUTE'),
          pg_catalog.has_function_privilege($2::pg_catalog.text,p.oid,'EXECUTE')
        FROM pg_catalog.pg_proc p
        JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
        WHERE p.prosecdef AND n.nspname NOT IN ('pg_catalog','information_schema')
          AND (pg_catalog.has_function_privilege($1::pg_catalog.text,p.oid,'EXECUTE')
            OR pg_catalog.has_function_privilege($2::pg_catalog.text,p.oid,'EXECUTE'))
        LIMIT 19
        """,
        [roles.lifecycle_login, roles.writer]
      )

    for [schema, name, lifecycle, writer] <- rows do
      remaining!(elem(context, 1))
      expected = Map.fetch!(CatalogManifest.functions(), name)
      require!(schema == "public" and writer and lifecycle == expected.runtime_execute)
    end

    # Function/type verification must not overlook a direct table/column escape
    # for its lifecycle login. This is a deny check, not relation admission.
    require!(
      query!(
        context,
        """
        SELECT 1 FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname NOT IN ('pg_catalog','information_schema')
          AND c.relkind IN ('r','p','v','m','f') AND (
            EXISTS (SELECT 1 FROM pg_catalog.aclexplode(
              COALESCE(c.relacl,pg_catalog.acldefault('r',c.relowner))) a
              WHERE a.grantee=0 OR a.grantee=(SELECT r.oid FROM pg_catalog.pg_roles r
                WHERE r.rolname=$1::pg_catalog.text))
            OR pg_catalog.has_table_privilege($1::pg_catalog.text,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
            OR EXISTS (SELECT 1 FROM pg_catalog.pg_attribute a
              WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped
                AND pg_catalog.has_column_privilege($1::pg_catalog.text,c.oid,a.attnum,'SELECT,INSERT,UPDATE,REFERENCES'))
            OR (pg_catalog.left(c.relname::pg_catalog.text,14)='mixer_browser_' AND (
              EXISTS (SELECT 1 FROM pg_catalog.aclexplode(
                COALESCE(c.relacl,pg_catalog.acldefault('r',c.relowner))) a
                WHERE CASE WHEN a.grantee=0 THEN true
                  ELSE pg_catalog.pg_has_role($2::pg_catalog.text,a.grantee,'MEMBER') END)
              OR pg_catalog.has_table_privilege($2::pg_catalog.text,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
              OR EXISTS (SELECT 1 FROM pg_catalog.pg_attribute a
                WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped
                  AND (pg_catalog.has_column_privilege($2::pg_catalog.text,c.oid,a.attnum,'SELECT,INSERT,UPDATE,REFERENCES')
                    OR EXISTS (SELECT 1 FROM pg_catalog.aclexplode(a.attacl) acl
                      WHERE CASE WHEN acl.grantee=0 THEN true
                        ELSE pg_catalog.pg_has_role($2::pg_catalog.text,acl.grantee,'MEMBER') END))))))
        LIMIT 1
        """,
        [roles.lifecycle_login, roles.ordinary_runtime_login]
      ) == []
    )
  end

  defp query!({repo, deadline}, sql, parameters \\ []) do
    %{rows: rows} =
      Ecto.Adapters.SQL.query!(repo, sql, parameters,
        queue: false,
        timeout: remaining!(deadline),
        log: false
      )

    remaining!(deadline)
    require!(length(rows) <= @catalog_row_limit)
    rows
  end

  defp remaining!(deadline) do
    remaining = deadline - System.monotonic_time(:millisecond)
    require!(remaining > 0)
    min(remaining, @query_limit_ms)
  end

  defp require!(true), do: :ok
  defp require!(_), do: raise(Unavailable)
end

