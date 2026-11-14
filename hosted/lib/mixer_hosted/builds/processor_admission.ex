defmodule MixerHosted.Builds.ProcessorAdmission do
  @moduledoc "Synchronous, read-only admission on the actual processor backend."
  use GenServer
  alias MixerHosted.Builds.ProcessorProfile, as: P

  def start_link(:builds_v1), do: GenServer.start_link(__MODULE__, :builds_v1)

  @impl true
  def init(:builds_v1) do
    case MixerHosted.Repo.transaction(fn ->
           check!(fn sql, params -> MixerHosted.Repo.query!(sql, params).rows end)
         end) do
      {:ok, :ok} -> {:ok, :admitted}
      _ -> {:stop, :processor_admission_refused}
    end
  end

  def after_connect(connection) do
    q = fn sql, params -> Postgrex.query!(connection, sql, params).rows end
    q.("BEGIN", [])

    try do
      :ok = check!(q)
      q.("COMMIT", [])
      :ok
    rescue
      error ->
        q.("ROLLBACK", [])
        reraise error, __STACKTRACE__
    end
  end

  @snapshot_sql ~S"""
  SELECT jsonb_build_object('backend_pid',pg_backend_pid(),'database',current_database(),'q00',(SELECT COALESCE(jsonb_agg(jsonb_build_array(t.c00,t.c01,t.c02,t.c03)), '[]'::jsonb) FROM (SELECT current_setting('server_version_num')::integer/10000,
          session_user::text,current_user::text,current_setting('transaction_isolation')) AS t(c00,c01,c02,c03)),'q01',(SELECT COALESCE(jsonb_agg(jsonb_build_array(t.c00,t.c01,t.c02,t.c03,t.c04,t.c05,t.c06,t.c07,t.c08,t.c09,t.c10,t.c11,t.c12,t.c13,t.c14,t.c15,t.c16)), '[]'::jsonb) FROM (SELECT r.rolname::text,r.rolcanlogin,r.rolsuper,r.rolbypassrls,r.rolcreatedb,
          r.rolcreaterole,r.rolreplication,r.rolinherit,r.rolconfig,r.rolconnlimit,
          r.rolvaliduntil IS NULL,
          NOT EXISTS(SELECT 1 FROM pg_auth_members WHERE member=r.oid OR roleid=r.oid),
          NOT EXISTS(SELECT 1 FROM pg_db_role_setting WHERE setrole=r.oid),
          NOT EXISTS(SELECT 1 FROM pg_namespace n WHERE has_schema_privilege(r.oid,n.oid,'CREATE')),
          NOT has_database_privilege(r.oid,current_database(),'CREATE,TEMPORARY'),
          NOT EXISTS(SELECT 1 FROM pg_shdepend d WHERE d.refclassid='pg_authid'::regclass
            AND d.refobjid=r.oid AND d.deptype='o' AND NOT
              (r.rolname='mixer_build_capacity_locker_v1' AND d.dbid=(SELECT oid FROM pg_database WHERE datname=current_database())
               AND d.classid='pg_proc'::regclass AND d.objid=to_regprocedure('public.mixer_build_capacity_lock_v1(text,text)'))),
          NOT EXISTS(SELECT 1 FROM pg_default_acl d CROSS JOIN LATERAL aclexplode(d.defaclacl) a
            WHERE d.defaclrole=r.oid OR a.grantee=r.oid OR a.grantee=0)
        FROM pg_roles r WHERE r.rolname=ANY(ARRAY['mixer_build_processor','mixer_build_capacity_locker_v1']::text[]::text[]) ORDER BY r.rolname) AS t(c00,c01,c02,c03,c04,c05,c06,c07,c08,c09,c10,c11,c12,c13,c14,c15,c16)),'q02/mixer_build_processor',(SELECT COALESCE(jsonb_agg(jsonb_build_array(t.c00,t.c01,t.c02,t.c03)), '[]'::jsonb) FROM (SELECT n.nspname::text,c.relname::text,p.privilege,
            has_table_privilege('mixer_build_processor',c.oid,p.privilege)
          FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
          CROSS JOIN unnest(ARRAY['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER','MAINTAIN']) p(privilege)
          WHERE c.relkind IN ('r','p','v','m','f') AND n.nspname !~ '^pg_' AND n.nspname<>'information_schema'
          ORDER BY n.nspname,c.relname,p.privilege LIMIT 8193) AS t(c00,c01,c02,c03)),'q02/mixer_build_capacity_locker_v1',(SELECT COALESCE(jsonb_agg(jsonb_build_array(t.c00,t.c01,t.c02,t.c03)), '[]'::jsonb) FROM (SELECT n.nspname::text,c.relname::text,p.privilege,
            has_table_privilege('mixer_build_capacity_locker_v1',c.oid,p.privilege)
          FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
          CROSS JOIN unnest(ARRAY['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER','MAINTAIN']) p(privilege)
          WHERE c.relkind IN ('r','p','v','m','f') AND n.nspname !~ '^pg_' AND n.nspname<>'information_schema'
          ORDER BY n.nspname,c.relname,p.privilege LIMIT 8193) AS t(c00,c01,c02,c03)),'q03/mixer_build_processor',(SELECT COALESCE(jsonb_agg(jsonb_build_array(t.c00,t.c01,t.c02,t.c03,t.c04)), '[]'::jsonb) FROM (SELECT n.nspname::text,c.relname::text,a.attname::text,p.privilege,
            has_column_privilege('mixer_build_processor',c.oid,a.attnum,p.privilege)
          FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
          JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped
          CROSS JOIN unnest(ARRAY['SELECT','INSERT','UPDATE','REFERENCES']) p(privilege)
          WHERE c.relkind IN ('r','p','v','m','f') AND n.nspname !~ '^pg_' AND n.nspname<>'information_schema'
          ORDER BY n.nspname,c.relname,a.attnum,p.privilege LIMIT 32769) AS t(c00,c01,c02,c03,c04)),'q03/mixer_build_capacity_locker_v1',(SELECT COALESCE(jsonb_agg(jsonb_build_array(t.c00,t.c01,t.c02,t.c03,t.c04)), '[]'::jsonb) FROM (SELECT n.nspname::text,c.relname::text,a.attname::text,p.privilege,
            has_column_privilege('mixer_build_capacity_locker_v1',c.oid,a.attnum,p.privilege)
          FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
          JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped
          CROSS JOIN unnest(ARRAY['SELECT','INSERT','UPDATE','REFERENCES']) p(privilege)
          WHERE c.relkind IN ('r','p','v','m','f') AND n.nspname !~ '^pg_' AND n.nspname<>'information_schema'
          ORDER BY n.nspname,c.relname,a.attnum,p.privilege LIMIT 32769) AS t(c00,c01,c02,c03,c04)),'q04/mixer_build_processor',(SELECT COALESCE(jsonb_agg(jsonb_build_array(t.c00,t.c01,t.c02,t.c03)), '[]'::jsonb) FROM (SELECT n.nspname::text,c.relname::text,p.privilege,has_sequence_privilege('mixer_build_processor',c.oid,p.privilege)
          FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
          CROSS JOIN unnest(ARRAY['SELECT','USAGE','UPDATE']) p(privilege)
          WHERE c.relkind='S' AND n.nspname !~ '^pg_' ORDER BY n.nspname,c.relname,p.privilege LIMIT 1025) AS t(c00,c01,c02,c03)),'q04/mixer_build_capacity_locker_v1',(SELECT COALESCE(jsonb_agg(jsonb_build_array(t.c00,t.c01,t.c02,t.c03)), '[]'::jsonb) FROM (SELECT n.nspname::text,c.relname::text,p.privilege,has_sequence_privilege('mixer_build_capacity_locker_v1',c.oid,p.privilege)
          FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
          CROSS JOIN unnest(ARRAY['SELECT','USAGE','UPDATE']) p(privilege)
          WHERE c.relkind='S' AND n.nspname !~ '^pg_' ORDER BY n.nspname,c.relname,p.privilege LIMIT 1025) AS t(c00,c01,c02,c03)),'q05/mixer_build_processor',(SELECT COALESCE(jsonb_agg(jsonb_build_array(t.c00)), '[]'::jsonb) FROM (SELECT NOT EXISTS(
            SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            CROSS JOIN LATERAL aclexplode(c.relacl) a
            WHERE n.nspname !~ '^pg_' AND a.grantee=(SELECT oid FROM pg_roles WHERE rolname='mixer_build_processor') AND a.is_grantable)
          AND NOT EXISTS(
            SELECT 1 FROM pg_attribute at CROSS JOIN LATERAL aclexplode(at.attacl) a
            WHERE a.grantee=(SELECT oid FROM pg_roles WHERE rolname='mixer_build_processor') AND a.is_grantable)) AS t(c00)),'q05/mixer_build_capacity_locker_v1',(SELECT COALESCE(jsonb_agg(jsonb_build_array(t.c00)), '[]'::jsonb) FROM (SELECT NOT EXISTS(
            SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            CROSS JOIN LATERAL aclexplode(c.relacl) a
            WHERE n.nspname !~ '^pg_' AND a.grantee=(SELECT oid FROM pg_roles WHERE rolname='mixer_build_capacity_locker_v1') AND a.is_grantable)
          AND NOT EXISTS(
            SELECT 1 FROM pg_attribute at CROSS JOIN LATERAL aclexplode(at.attacl) a
            WHERE a.grantee=(SELECT oid FROM pg_roles WHERE rolname='mixer_build_capacity_locker_v1') AND a.is_grantable)) AS t(c00)),'q06/mixer_build_processor',(SELECT COALESCE(jsonb_agg(jsonb_build_array(t.c00,t.c01,t.c02,t.c03,t.c04)), '[]'::jsonb) FROM (SELECT n.nspname::text,c.relname::text,a.privilege_type,g.rolname::text,a.is_grantable
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
          CROSS JOIN LATERAL aclexplode(c.relacl) a JOIN pg_roles g ON g.oid=a.grantor
        WHERE a.grantee=(SELECT oid FROM pg_roles WHERE rolname='mixer_build_processor')
          AND n.nspname !~ '^pg_' AND c.relkind IN ('r','p','v','m','f','S')
        ORDER BY n.nspname,c.relname,a.privilege_type LIMIT 129) AS t(c00,c01,c02,c03,c04)),'q06/mixer_build_capacity_locker_v1',(SELECT COALESCE(jsonb_agg(jsonb_build_array(t.c00,t.c01,t.c02,t.c03,t.c04)), '[]'::jsonb) FROM (SELECT n.nspname::text,c.relname::text,a.privilege_type,g.rolname::text,a.is_grantable
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
          CROSS JOIN LATERAL aclexplode(c.relacl) a JOIN pg_roles g ON g.oid=a.grantor
        WHERE a.grantee=(SELECT oid FROM pg_roles WHERE rolname='mixer_build_capacity_locker_v1')
          AND n.nspname !~ '^pg_' AND c.relkind IN ('r','p','v','m','f','S')
        ORDER BY n.nspname,c.relname,a.privilege_type LIMIT 129) AS t(c00,c01,c02,c03,c04)),'q07/mixer_build_processor',(SELECT COALESCE(jsonb_agg(jsonb_build_array(t.c00,t.c01,t.c02,t.c03,t.c04,t.c05)), '[]'::jsonb) FROM (SELECT n.nspname::text,c.relname::text,at.attname::text,a.privilege_type,g.rolname::text,a.is_grantable
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
          JOIN pg_attribute at ON at.attrelid=c.oid AND at.attnum>0 AND NOT at.attisdropped
          CROSS JOIN LATERAL aclexplode(at.attacl) a JOIN pg_roles g ON g.oid=a.grantor
        WHERE a.grantee=(SELECT oid FROM pg_roles WHERE rolname='mixer_build_processor')
          AND n.nspname !~ '^pg_'
        ORDER BY n.nspname,c.relname,at.attname,a.privilege_type LIMIT 129) AS t(c00,c01,c02,c03,c04,c05)),'q07/mixer_build_capacity_locker_v1',(SELECT COALESCE(jsonb_agg(jsonb_build_array(t.c00,t.c01,t.c02,t.c03,t.c04,t.c05)), '[]'::jsonb) FROM (SELECT n.nspname::text,c.relname::text,at.attname::text,a.privilege_type,g.rolname::text,a.is_grantable
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
          JOIN pg_attribute at ON at.attrelid=c.oid AND at.attnum>0 AND NOT at.attisdropped
          CROSS JOIN LATERAL aclexplode(at.attacl) a JOIN pg_roles g ON g.oid=a.grantor
        WHERE a.grantee=(SELECT oid FROM pg_roles WHERE rolname='mixer_build_capacity_locker_v1')
          AND n.nspname !~ '^pg_'
        ORDER BY n.nspname,c.relname,at.attname,a.privilege_type LIMIT 129) AS t(c00,c01,c02,c03,c04,c05)),'q08/mixer_build_processor',(SELECT COALESCE(jsonb_agg(jsonb_build_array(t.c00)), '[]'::jsonb) FROM (SELECT count(*)=1 AND bool_and(n.nspname='public' AND a.privilege_type='USAGE'
          AND a.grantor=n.nspowner AND NOT a.is_grantable)
        FROM pg_namespace n CROSS JOIN LATERAL aclexplode(n.nspacl) a
        WHERE a.grantee=(SELECT oid FROM pg_roles WHERE rolname='mixer_build_processor')) AS t(c00)),'q08/mixer_build_capacity_locker_v1',(SELECT COALESCE(jsonb_agg(jsonb_build_array(t.c00)), '[]'::jsonb) FROM (SELECT count(*)=1 AND bool_and(n.nspname='public' AND a.privilege_type='USAGE'
          AND a.grantor=n.nspowner AND NOT a.is_grantable)
        FROM pg_namespace n CROSS JOIN LATERAL aclexplode(n.nspacl) a
        WHERE a.grantee=(SELECT oid FROM pg_roles WHERE rolname='mixer_build_capacity_locker_v1')) AS t(c00)),'q09',(SELECT COALESCE(jsonb_agg(jsonb_build_array(t.c00,t.c01,t.c02,t.c03,t.c04,t.c05,t.c06,t.c07,t.c08,t.c09,t.c10,t.c11,t.c12)), '[]'::jsonb) FROM (SELECT p.prosrc,p.prosecdef,p.provolatile::text,p.proparallel::text,p.proleakproof,
          p.proconfig,l.lanname::text,p.prorettype::regtype::text,oidvectortypes(p.proargtypes),p.proargnames,
          p.pronargdefaults,o.rolname::text,p.proisstrict
        FROM pg_proc p JOIN pg_language l ON l.oid=p.prolang JOIN pg_roles o ON o.oid=p.proowner
        WHERE p.oid=to_regprocedure('public.mixer_build_capacity_lock_v1(text,text)')) AS t(c00,c01,c02,c03,c04,c05,c06,c07,c08,c09,c10,c11,c12)),'q10',(SELECT COALESCE(jsonb_agg(jsonb_build_array(t.c00,t.c01,t.c02,t.c03)), '[]'::jsonb) FROM (SELECT r.rolname::text,g.rolname::text,a.privilege_type,a.is_grantable
        FROM pg_proc p CROSS JOIN LATERAL aclexplode(p.proacl) a
          JOIN pg_roles r ON r.oid=a.grantee JOIN pg_roles g ON g.oid=a.grantor
        WHERE p.oid=to_regprocedure('public.mixer_build_capacity_lock_v1(text,text)') ORDER BY r.rolname) AS t(c00,c01,c02,c03)),'q11',(SELECT COALESCE(jsonb_agg(jsonb_build_array(t.c00)), '[]'::jsonb) FROM (SELECT NOT EXISTS(SELECT 1 FROM pg_proc p CROSS JOIN LATERAL aclexplode(p.proacl) a WHERE p.oid=to_regprocedure('public.mixer_build_capacity_lock_v1(text,text)') AND a.grantee=0)) AS t(c00)),'q12/mixer_build_processor',(SELECT COALESCE(jsonb_agg(jsonb_build_array(t.c00)), '[]'::jsonb) FROM (SELECT p.oid::regprocedure::text FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
          WHERE n.nspname !~ '^pg_' AND n.nspname<>'information_schema' AND has_function_privilege('mixer_build_processor',p.oid,'EXECUTE')
          ORDER BY p.oid LIMIT 2) AS t(c00)),'q12/mixer_build_capacity_locker_v1',(SELECT COALESCE(jsonb_agg(jsonb_build_array(t.c00)), '[]'::jsonb) FROM (SELECT p.oid::regprocedure::text FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
          WHERE n.nspname !~ '^pg_' AND n.nspname<>'information_schema' AND has_function_privilege('mixer_build_capacity_locker_v1',p.oid,'EXECUTE')
          ORDER BY p.oid LIMIT 2) AS t(c00)),'q13',(SELECT COALESCE(jsonb_agg(jsonb_build_array(t.c00,t.c01,t.c02,t.c03,t.c04,t.c05,t.c06)), '[]'::jsonb) FROM (SELECT c.relname::text,p.polname::text,p.polcmd::text,p.polpermissive,
          ARRAY(SELECT r.rolname::text FROM pg_roles r WHERE r.oid=ANY(p.polroles) ORDER BY r.rolname),
          pg_get_expr(p.polqual,p.polrelid,false),pg_get_expr(p.polwithcheck,p.polrelid,false)
        FROM pg_policy p JOIN pg_class c ON c.oid=p.polrelid JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relname=ANY(ARRAY['mixer_build_fleet_capacity','mixer_build_fleet_platform_capacities','mixer_build_organization_capacities','mixer_build_capacities','mixer_builds','mixer_build_reservations','mixer_build_coordinator_leases','oban_jobs','oban_peers','mixer_customer_build_inputs']::text[]::text[])
        ORDER BY c.relname,p.polname LIMIT 47) AS t(c00,c01,c02,c03,c04,c05,c06)),'q14',(SELECT COALESCE(jsonb_agg(jsonb_build_array(t.c00)), '[]'::jsonb) FROM (SELECT count(*)=10 AND bool_and(c.relrowsecurity AND c.relforcerowsecurity AND r.rolname='browser_schema_owner')
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_roles r ON r.oid=c.relowner
        WHERE n.nspname='public' AND c.relname=ANY(ARRAY['mixer_build_fleet_capacity','mixer_build_fleet_platform_capacities','mixer_build_organization_capacities','mixer_build_capacities','mixer_builds','mixer_build_reservations','mixer_build_coordinator_leases','oban_jobs','oban_peers','mixer_customer_build_inputs']::text[]::text[])) AS t(c00)))::text
  """

  def snapshot_sql, do: @snapshot_sql

  def decode!(raw) when is_binary(raw) and byte_size(raw) <= 8_388_608 do
    snapshot = Jason.decode!(raw)
    true = is_map(snapshot)
    snapshot
  end

  def validate!(snapshot) do
    true = is_integer(snapshot["backend_pid"]) and snapshot["backend_pid"] > 0
    true = is_binary(snapshot["database"]) and byte_size(snapshot["database"]) > 0

    true =
      MapSet.new(Map.keys(snapshot)) ==
        MapSet.new([
          "backend_pid",
          "database",
          "q00",
          "q01",
          "q02/mixer_build_processor",
          "q02/mixer_build_capacity_locker_v1",
          "q03/mixer_build_processor",
          "q03/mixer_build_capacity_locker_v1",
          "q04/mixer_build_processor",
          "q04/mixer_build_capacity_locker_v1",
          "q05/mixer_build_processor",
          "q05/mixer_build_capacity_locker_v1",
          "q06/mixer_build_processor",
          "q06/mixer_build_capacity_locker_v1",
          "q07/mixer_build_processor",
          "q07/mixer_build_capacity_locker_v1",
          "q08/mixer_build_processor",
          "q08/mixer_build_capacity_locker_v1",
          "q09",
          "q10",
          "q11",
          "q12/mixer_build_processor",
          "q12/mixer_build_capacity_locker_v1",
          "q13",
          "q14"
        ])

    identity!(snapshot)
    privileges!(snapshot)
    functions!(snapshot)
    policies!(snapshot)
    :ok
  end

  def check!(q) do
    [[original_path]] = q.("SELECT current_setting('search_path')", [])
    q.("SELECT set_config('search_path','pg_catalog',true)", [])
    [[raw]] = q.(@snapshot_sql, [])
    # Restore before validation so a contract refusal cannot be masked by an aborted query.
    q.("SELECT set_config('search_path',$1,true)", [original_path])
    raw |> decode!() |> validate!()
  end

  defp rows(snapshot, key), do: Map.fetch!(snapshot, key)
  defp rows(snapshot, key, role), do: Map.fetch!(snapshot, key <> "/" <> role)

  defp identity!(snapshot) do
    [[17, login, login, "read committed"]] =
      rows(snapshot, "q00")

    true = login == P.role()

    rows =
      rows(snapshot, "q01")

    expected =
      for r <- Enum.sort([P.role(), P.locker()]),
          do: [
            r,
            r == P.role(),
            false,
            false,
            false,
            false,
            false,
            false,
            nil,
            -1,
            true,
            true,
            true,
            true,
            true,
            true,
            true
          ]

    true = rows == expected
  end

  defp privileges!(snapshot) do
    for role <- [P.role(), P.locker()] do
      rights = P.table_rights(role)

      table_rows =
        rows(snapshot, "q02", role)

      true = length(table_rows) < 8193

      for [schema, table, right, actual] <- table_rows do
        expected = schema == "public" and right in nil_list(get_in(rights, [table, :table]))
        true = actual == expected
      end

      columns =
        rows(snapshot, "q03", role)

      true = length(columns) < 32769

      for [schema, table, col, right, actual] <- columns do
        t = Map.get(rights, table, %{table: [], columns: %{}})

        expected =
          schema == "public" and (right in t.table or col in Map.get(t.columns, right, []))

        true = actual == expected
      end

      true =
        Enum.all?(Map.keys(rights), fn t ->
          Enum.any?(table_rows, fn [s, n, _, _] -> s == "public" and n == t end)
        end)

      explicit_acl!(snapshot, role, rights)

      sequences =
        rows(snapshot, "q04", role)

      true = length(sequences) < 1025

      for [schema, name, right, actual] <- sequences do
        true =
          actual ==
            (role == P.role() and schema == "public" and name == "oban_jobs_id_seq" and
               right == "USAGE")
      end

      [[true]] =
        rows(snapshot, "q05", role)
    end
  end

  defp explicit_acl!(snapshot, role, rights) do
    actual =
      rows(snapshot, "q06", role)

    expected =
      for {table, r} <- rights,
          right <- r.table,
          do: ["public", table, right, "browser_schema_owner", false]

    expected =
      if role == P.role(),
        do: [["public", "oban_jobs_id_seq", "USAGE", "browser_schema_owner", false] | expected],
        else: expected

    true = actual == Enum.sort(expected)

    actual_columns =
      rows(snapshot, "q07", role)

    expected_columns =
      for {table, r} <- rights,
          {right, cols} <- r.columns,
          col <- cols,
          do: ["public", table, col, right, "browser_schema_owner", false]

    true = actual_columns == Enum.sort(expected_columns)

    [[true]] =
      rows(snapshot, "q08", role)
  end

  defp nil_list(nil), do: []
  defp nil_list(list), do: list

  defp functions!(snapshot) do
    [
      [
        source,
        true,
        "v",
        "u",
        false,
        ["search_path=pg_catalog"],
        "plpgsql",
        "void",
        "text, text",
        ["org", "plat"],
        0,
        owner,
        false
      ]
    ] =
      rows(snapshot, "q09")

    true = source == P.body() and owner == P.locker()

    acls =
      rows(snapshot, "q10")

    true =
      acls ==
        for r <- Enum.sort([P.locker(), P.role(), "browser_schema_owner"]),
            do: [r, P.locker(), "EXECUTE", false]

    [[true]] =
      rows(snapshot, "q11")

    for role <- [P.role(), P.locker()] do
      rows =
        rows(snapshot, "q12", role)

      true = rows == [[P.function()]]
    end
  end

  defp policies!(snapshot) do
    tables = Map.keys(P.table_rights(P.role())) ++ ["mixer_customer_build_inputs"]
    true = length(tables) == 10

    rows =
      rows(snapshot, "q13")

    expected =
      P.auxiliary_policies() ++
        MixerHosted.CustomerBuilds.CreateSchema.expected_policies(:builds_v1)

    true = rows == Enum.sort_by(expected, fn [t, n | _] -> {t, n} end)

    [[true]] =
      rows(snapshot, "q14")
  end
end
