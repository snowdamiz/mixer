defmodule MixerHosted.BrowserAuth.RelationCatalog do
  @moduledoc """
  Bounded private relation prerequisite. The trusted Store must independently own
  the Repo, checkout, original deadline, function prerequisite and rollback.
  This function is not a storage/readiness/owner admission receipt.
  """
  alias MixerHosted.BrowserAuth.RelationManifest
  @roles [:lifecycle_login, :writer, :relation_owner, :ordinary_runtime_login]
  @marker "__mixer_relation_bound__"
  @wire_limit 2 * 1024 * 1024
  @function_settings [
    "search_path=pg_catalog",
    "statement_timeout=5s",
    "lock_timeout=500ms",
    "idle_in_transaction_session_timeout=5s",
    "bytea_output=hex"
  ]

  defmodule Unavailable do
    @moduledoc false
    defexception message: "browser storage unavailable"
  end

  @doc false
  def check_relation_surface!(repo, expected_roles, original_monotonic_deadline_ms) do
    try do
      check_roles!(expected_roles)
      deadline = original_monotonic_deadline_ms
      remaining!(deadline)
      demand(is_atom(repo) and repo.in_transaction?() === true)
      state = %{repo: repo, deadline: deadline, wire: 0}
      {context, state} = context!(state, expected_roles)
      {role_oids, state} = roles!(state, expected_roles)
      manifest = RelationManifest.for_major(context.major)
      {relations, state} = relations!(state, role_oids)
      ids = Enum.map(relations, & &1["oid"])
      {columns, state} = columns!(state, ids, manifest)
      {constraints, state} = constraints!(state, ids, columns, manifest)
      {indexes, state} = indexes!(state, ids, columns, constraints, manifest, role_oids)
      {_, state} = triggers!(state, ids, constraints, indexes, manifest, role_oids)
      {_, state} = policies!(state, ids, manifest, role_oids)
      {_, state} = privileges!(state, ids, columns, manifest, role_oids, context.major)
      {_, state} = forbidden!(state, ids, role_oids, context.major)
      remaining!(state.deadline)
      :relation_surface_verified
    rescue
      _ -> raise Unavailable
    catch
      _, _ -> raise Unavailable
    end
  end

  defp demand(true), do: :ok
  defp demand(_), do: raise(Unavailable)

  defp check_roles!(roles) do
    demand(
      is_map(roles) and map_size(roles) == 4 and Enum.sort(Map.keys(roles)) == Enum.sort(@roles)
    )

    values = Map.values(roles)
    demand(length(Enum.uniq(values)) == 4 and Enum.all?(values, &role?/1))
  end

  defp role?(name) when is_binary(name) and byte_size(name) in 1..63 do
    name != "public" and not String.starts_with?(name, "pg_") and
      Enum.all?(Enum.with_index(:binary.bin_to_list(name)), fn {c, i} ->
        c in ?a..?z or c == ?_ or (i > 0 and c in ?0..?9)
      end)
  end

  defp role?(_), do: false

  defp remaining!(deadline) when is_integer(deadline) do
    remaining = deadline - System.monotonic_time(:millisecond)
    demand(remaining > 0 and remaining <= 5_000)
    remaining
  end

  defp remaining!(_), do: raise(Unavailable)

  # Closed wire shapes. Nullability is explicit; false never stands for NULL.
  defp fetch!(state, sql, params, schema, cap, expected_count) do
    remaining = remaining!(state.deadline)

    result =
      Ecto.Adapters.SQL.query!(state.repo, sql, params,
        timeout: remaining,
        queue: false,
        log: false
      )

    remaining!(state.deadline)
    %{columns: names, rows: rows, num_rows: count} = result
    demand(names === Enum.map(schema, &elem(&1, 0)))
    demand(is_list(rows) and is_integer(count) and count == length(rows) and count <= cap)
    demand(is_nil(expected_count) or count == expected_count)

    {decoded, state} =
      Enum.map_reduce(rows, state, fn row, acc ->
        remaining!(acc.deadline)
        demand(is_list(row) and length(row) == length(schema))

        {fields, bytes} =
          Enum.map_reduce(Enum.zip(schema, row), 0, fn {{name, type}, value}, sum ->
            size = typed!(value, type)
            {{name, value}, sum + 4 + size}
          end)

        next = %{acc | wire: acc.wire + bytes}
        demand(next.wire <= @wire_limit)
        remaining!(next.deadline)
        {Map.new(fields), next}
      end)

    remaining!(state.deadline)
    {decoded, state}
  end

  defp typed!(nil, {:nullable, _}), do: 0
  defp typed!(value, {:nullable, type}), do: typed!(value, type)
  defp typed!(value, :bool) when is_boolean(value), do: 1
  defp typed!(value, :int) when is_integer(value), do: 8
  defp typed!(value, :oid) when is_integer(value) and value >= 0 and value <= 4_294_967_295, do: 8

  defp typed!(value, {:text, cap}) when is_binary(value) do
    demand(byte_size(value) <= cap and String.valid?(value) and value != @marker)
    byte_size(value)
  end

  defp typed!(value, {:array, type, cap}) when is_list(value) do
    demand(length(value) <= cap)
    Enum.reduce(value, 20, fn x, n -> n + 4 + typed!(x, type) end)
  end

  defp typed!(_, _), do: raise(Unavailable)

  defp expr(node, relation) do
    "CASE WHEN #{node} IS NULL THEN NULL WHEN pg_catalog.octet_length(#{node}::pg_catalog.text)>32768 THEN '#{@marker}' ELSE CASE WHEN pg_catalog.octet_length(pg_catalog.pg_get_expr(#{node},#{relation},false))>8192 THEN '#{@marker}' ELSE pg_catalog.pg_get_expr(#{node},#{relation},false) END END"
  end

  defp acl_ok(acl) do
    "(#{acl} IS NULL OR (pg_catalog.cardinality(#{acl})<=64 AND pg_catalog.octet_length(#{acl}::pg_catalog.text)<=16384))"
  end

  defp context!(state, roles) do
    schema = [
      {"login", {:text, 63}},
      {"session", {:text, 63}},
      {"version", :int},
      {"isolation", {:text, 32}},
      {"path", {:text, 128}},
      {"jit", {:text, 8}},
      {"statement", {:text, 32}},
      {"lock", {:text, 32}},
      {"idle", {:text, 32}},
      {"bytea", {:text, 8}},
      {"replication", {:text, 16}},
      {"encoding", {:text, 16}},
      {"collate", {:text, 128}},
      {"ctype", {:text, 128}},
      {"provider", {:text, 8}},
      {"stored_version", {:nullable, {:text, 256}}},
      {"actual_version", {:nullable, {:text, 256}}}
    ]

    sql = """
    SELECT current_user::pg_catalog.text AS login, session_user::pg_catalog.text AS session,
      pg_catalog.current_setting('server_version_num')::pg_catalog.int4 AS version,
      pg_catalog.current_setting('transaction_isolation') AS isolation,
      pg_catalog.current_setting('search_path') AS path, pg_catalog.current_setting('jit') AS jit,
      pg_catalog.current_setting('statement_timeout') AS statement, pg_catalog.current_setting('lock_timeout') AS lock,
      pg_catalog.current_setting('idle_in_transaction_session_timeout') AS idle,
      pg_catalog.current_setting('bytea_output') AS bytea, pg_catalog.current_setting('session_replication_role') AS replication,
      pg_catalog.current_setting('server_encoding') AS encoding, d.datcollate::pg_catalog.text AS collate,
      d.datctype::pg_catalog.text AS ctype, d.datlocprovider::pg_catalog.text AS provider,
      d.datcollversion::pg_catalog.text AS stored_version,
      pg_catalog.pg_database_collation_actual_version(d.oid)::pg_catalog.text AS actual_version
    FROM pg_catalog.pg_database d WHERE d.datname=pg_catalog.current_database() LIMIT 2
    """

    {[row], state} = fetch!(state, sql, [], schema, 1, 1)
    demand(row["login"] === roles.lifecycle_login and row["session"] === roles.lifecycle_login)
    major = div(row["version"], 10_000)
    demand(major in [16, 17])

    demand(
      Map.drop(row, ["login", "session", "version"]) === %{
        "isolation" => "read committed",
        "path" => "pg_catalog",
        "jit" => "off",
        "statement" => "5s",
        "lock" => "500ms",
        "idle" => "5s",
        "bytea" => "hex",
        "replication" => "origin",
        "encoding" => "UTF8",
        "collate" => "C",
        "ctype" => "C",
        "provider" => "c",
        "stored_version" => nil,
        "actual_version" => nil
      }
    )

    {%{major: major}, state}
  end

  defp roles!(state, roles) do
    schema = [
      {"name", {:text, 63}},
      {"oid", :oid},
      {"login", :bool},
      {"unsafe", :bool},
      {"edges", :bool}
    ]

    sql = """
    SELECT r.rolname::pg_catalog.text AS name, r.oid::pg_catalog.int8 AS oid, r.rolcanlogin AS login,
      (r.rolsuper OR r.rolbypassrls OR r.rolcreaterole OR r.rolcreatedb OR r.rolreplication OR r.rolinherit) AS unsafe,
      EXISTS(SELECT 1 FROM pg_catalog.pg_auth_members m WHERE m.roleid=r.oid OR m.member=r.oid) AS edges
    FROM pg_catalog.pg_roles r WHERE r.rolname=ANY($1::pg_catalog.text[]) ORDER BY r.oid LIMIT 5
    """

    {rows, state} = fetch!(state, sql, [Map.values(roles)], schema, 4, 4)
    names = Map.new(rows, &{&1["name"], &1})

    for key <- @roles do
      row = Map.fetch!(names, roles[key])
      demand(row["oid"] > 0 and not row["unsafe"] and not row["edges"])
      demand(row["login"] === key in [:lifecycle_login, :ordinary_runtime_login])
    end

    {Map.new(@roles, &{&1, Map.fetch!(names, roles[&1])["oid"]}), state}
  end

  defp relations!(state, roles) do
    schema = [
      {"name", {:text, 127}},
      {"oid", :oid},
      {"kind", {:text, 1}},
      {"persistence", {:text, 1}},
      {"owner", :oid},
      {"rls", :bool},
      {"force", :bool},
      {"partition", :bool},
      {"typed", :oid},
      {"replica", {:text, 1}},
      {"bound", {:nullable, {:text, 8192}}},
      {"acl_ok", :bool}
    ]

    sql = """
    SELECT n.nspname::pg_catalog.text||'.'||c.relname::pg_catalog.text AS name, c.oid::pg_catalog.int8 AS oid,
      c.relkind::pg_catalog.text AS kind,c.relpersistence::pg_catalog.text AS persistence,c.relowner::pg_catalog.int8 AS owner,
      c.relrowsecurity AS rls,c.relforcerowsecurity AS force,c.relispartition AS partition,c.reloftype::pg_catalog.int8 AS typed,
      c.relreplident::pg_catalog.text AS replica,#{expr("c.relpartbound", "c.oid")} AS bound,#{acl_ok("c.relacl")} AS acl_ok
    FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
    WHERE (n.nspname='public' AND n.nspname::pg_catalog.text||'.'||c.relname::pg_catalog.text=ANY($1::pg_catalog.text[]))
       OR (pg_catalog.left(c.relname::pg_catalog.text,14)='mixer_browser_' AND c.relkind IN('r','p','v','m','f'))
    ORDER BY n.nspname,c.relname,c.oid LIMIT 10
    """

    {rows, state} = fetch!(state, sql, [RelationManifest.names()], schema, 9, 9)
    demand(Enum.sort(Enum.map(rows, & &1["name"])) === RelationManifest.names())
    demand(length(Enum.uniq(Enum.map(rows, & &1["oid"]))) == 9)

    each!(rows, state, fn r ->
      demand(
        r["oid"] > 0 and
          Map.drop(r, ["name", "oid"]) === %{
            "kind" => "r",
            "persistence" => "p",
            "owner" => roles.relation_owner,
            "rls" => true,
            "force" => true,
            "partition" => false,
            "typed" => 0,
            "replica" => "d",
            "bound" => nil,
            "acl_ok" => true
          }
      )
    end)

    {rows, state}
  end

  defp each!(rows, state, fun) do
    Enum.each(rows, fn row ->
      remaining!(state.deadline)
      fun.(row)
      remaining!(state.deadline)
    end)
  end

  defp names_cte do
    "WITH targets AS (SELECT c.oid,n.nspname::pg_catalog.text||'.'||c.relname::pg_catalog.text AS name FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE c.oid=ANY($1::pg_catalog.oid[])) "
  end

  defp columns!(state, ids, manifest) do
    schema = [
      {"relation", {:text, 127}},
      {"relid", :oid},
      {"number", :int},
      {"name", {:text, 63}},
      {"dropped", :bool},
      {"type_oid", :oid},
      {"type", {:text, 127}},
      {"base", :oid},
      {"type_kind", {:text, 1}},
      {"typmod", :int},
      {"dimensions", :int},
      {"notnull", :bool},
      {"identity", {:text, 1}},
      {"generated", {:text, 1}},
      {"local", :bool},
      {"inherited", :int},
      {"has_default", :bool},
      {"default", {:nullable, {:text, 8192}}},
      {"has_missing", :bool},
      {"missing", {:nullable, {:text, 16384}}},
      {"collation_oid", :oid},
      {"collation", {:nullable, {:text, 127}}},
      {"collation_safe", :bool},
      {"acl_null", :bool},
      {"acl_ok", :bool}
    ]

    sql =
      names_cte() <>
        """
        SELECT x.name AS relation,a.attrelid::pg_catalog.int8 AS relid,a.attnum::pg_catalog.int4 AS number,
          a.attname::pg_catalog.text AS name,a.attisdropped AS dropped,a.atttypid::pg_catalog.int8 AS type_oid,
          tn.nspname::pg_catalog.text||'.'||t.typname::pg_catalog.text AS type,t.typbasetype::pg_catalog.int8 AS base,
          t.typtype::pg_catalog.text AS type_kind,a.atttypmod AS typmod,a.attndims AS dimensions,a.attnotnull AS notnull,
          a.attidentity::pg_catalog.text AS identity,a.attgenerated::pg_catalog.text AS generated,a.attislocal AS local,
          a.attinhcount AS inherited,a.atthasdef AS has_default,#{expr("d.adbin", "a.attrelid")} AS default,
          a.atthasmissing AS has_missing,
          CASE WHEN a.attmissingval IS NULL THEN NULL WHEN pg_catalog.cardinality(a.attmissingval)>1 OR pg_catalog.octet_length(a.attmissingval::pg_catalog.text)>16384 THEN '#{@marker}' ELSE a.attmissingval::pg_catalog.text END AS missing,
          a.attcollation::pg_catalog.int8 AS collation_oid,
          CASE WHEN a.attcollation=0 THEN NULL ELSE cn.nspname::pg_catalog.text||'.'||co.collname::pg_catalog.text END AS collation,
          (a.attcollation=0 OR (co.collprovider='d' AND co.collisdeterministic AND co.collencoding=-1 AND co.collcollate IS NULL AND co.collctype IS NULL AND co.collversion IS NULL)) AS collation_safe,
          a.attacl IS NULL AS acl_null,#{acl_ok("a.attacl")} AS acl_ok
        FROM targets x JOIN pg_catalog.pg_attribute a ON a.attrelid=x.oid
        JOIN pg_catalog.pg_type t ON t.oid=a.atttypid JOIN pg_catalog.pg_namespace tn ON tn.oid=t.typnamespace
        LEFT JOIN pg_catalog.pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum
        LEFT JOIN pg_catalog.pg_collation co ON co.oid=a.attcollation LEFT JOIN pg_catalog.pg_namespace cn ON cn.oid=co.collnamespace
        WHERE a.attnum>0 ORDER BY x.name,a.attnum LIMIT 125
        """

    {rows, state} = fetch!(state, sql, [ids], schema, 124, 124)

    types = %{
      "integer" => "int4",
      "bigint" => "int8",
      "boolean" => "bool",
      "bytea" => "bytea",
      "text" => "text"
    }

    each!(Map.to_list(manifest["structure"]["relations"]), state, fn {rel, spec} ->
      actual = Enum.filter(rows, &(&1["relation"] == rel))
      demand(length(actual) == length(spec["columns"]))

      each!(Enum.with_index(Enum.zip(actual, spec["columns"]), 1), state, fn {{r, c}, i} ->
        typ = Map.fetch!(types, c["type"])

        demand(
          r["name"] === c["name"] and r["number"] === i and r["type"] === "pg_catalog." <> typ and
            r["type_oid"] > 0
        )

        demand(
          not r["dropped"] and r["base"] == 0 and r["type_kind"] == "b" and r["typmod"] == -1 and
            r["dimensions"] == 0
        )

        demand(
          r["notnull"] === not c["nullable"] and r["identity"] == "" and r["generated"] == "" and
            r["local"] and r["inherited"] == 0
        )

        demand(r["default"] === c["default"] and r["has_default"] === not is_nil(c["default"]))

        fast =
          {rel, c["name"]} in [
            {"public.mixer_authz_profiles", "state_revision"},
            {"public.mixer_authz_bindings", "revision"}
          ]

        demand(
          (not r["has_missing"] and is_nil(r["missing"])) or
            (fast and r["has_missing"] and r["missing"] == "{1}")
        )

        demand(
          r["collation_safe"] and
            r["collation"] === if(typ == "text", do: "pg_catalog.default", else: nil)
        )

        demand(r["collation_oid"] > 0 === (typ == "text") and r["acl_ok"])
        mutable = c["name"] in manifest["structure"]["writer_grants"][rel]["update_columns"]
        demand(r["acl_null"] === not mutable)
      end)
    end)

    {rows, state}
  end

  defp key_names(array, rel) do
    "CASE WHEN pg_catalog.cardinality(#{array})>32 THEN ARRAY['#{@marker}']::pg_catalog.text[] ELSE ARRAY(SELECT a.attname::pg_catalog.text FROM pg_catalog.unnest(#{array}) WITH ORDINALITY k(num,ord) LEFT JOIN pg_catalog.pg_attribute a ON a.attrelid=#{rel} AND a.attnum=k.num ORDER BY k.ord) END"
  end

  defp operators(array) do
    "CASE WHEN pg_catalog.cardinality(#{array})>32 THEN ARRAY['#{@marker}']::pg_catalog.text[] ELSE ARRAY(SELECT n.nspname::pg_catalog.text||'.'||o.oprname::pg_catalog.text||':'||ln.nspname::pg_catalog.text||'.'||l.typname::pg_catalog.text||':'||rn.nspname::pg_catalog.text||'.'||r.typname::pg_catalog.text FROM pg_catalog.unnest(#{array}) WITH ORDINALITY k(id,ord) LEFT JOIN pg_catalog.pg_operator o ON o.oid=k.id LEFT JOIN pg_catalog.pg_namespace n ON n.oid=o.oprnamespace LEFT JOIN pg_catalog.pg_type l ON l.oid=o.oprleft LEFT JOIN pg_catalog.pg_namespace ln ON ln.oid=l.typnamespace LEFT JOIN pg_catalog.pg_type r ON r.oid=o.oprright LEFT JOIN pg_catalog.pg_namespace rn ON rn.oid=r.typnamespace ORDER BY k.ord) END"
  end

  defp constraints!(state, ids, columns, manifest) do
    schema = [
      {"oid", :oid},
      {"relid", :oid},
      {"relation", {:text, 127}},
      {"kind", {:text, 1}},
      {"deferrable", :bool},
      {"deferred", :bool},
      {"validated", :bool},
      {"local", :bool},
      {"inherited", :int},
      {"noinherit", :bool},
      {"parent", :oid},
      {"domain", :oid},
      {"target_oid", :oid},
      {"target", {:nullable, {:text, 127}}},
      {"keys", {:array, {:text, 63}, 32}},
      {"target_keys", {:array, {:text, 63}, 32}},
      {"match", {:text, 1}},
      {"update", {:text, 1}},
      {"delete", {:text, 1}},
      {"index", :oid},
      {"pfeq", {:array, {:text, 256}, 32}},
      {"ppeq", {:array, {:text, 256}, 32}},
      {"ffeq", {:array, {:text, 256}, 32}},
      {"expression", {:nullable, {:text, 8192}}},
      {"excluded", :bool},
      {"delete_columns", :bool}
    ]

    sql =
      names_cte() <>
        """
        SELECT c.oid::pg_catalog.int8 AS oid,c.conrelid::pg_catalog.int8 AS relid,
          n.nspname::pg_catalog.text||'.'||r.relname::pg_catalog.text AS relation,c.contype::pg_catalog.text AS kind,
          c.condeferrable AS deferrable,c.condeferred AS deferred,c.convalidated AS validated,c.conislocal AS local,
          c.coninhcount AS inherited,c.connoinherit AS noinherit,c.conparentid::pg_catalog.int8 AS parent,c.contypid::pg_catalog.int8 AS domain,
          c.confrelid::pg_catalog.int8 AS target_oid,
          CASE WHEN c.confrelid=0 THEN NULL ELSE tn.nspname::pg_catalog.text||'.'||tr.relname::pg_catalog.text END AS target,
          #{key_names("c.conkey", "c.conrelid")} AS keys,#{key_names("c.confkey", "c.confrelid")} AS target_keys,
          c.confmatchtype::pg_catalog.text AS match,c.confupdtype::pg_catalog.text AS update,c.confdeltype::pg_catalog.text AS delete,
          c.conindid::pg_catalog.int8 AS index,#{operators("c.conpfeqop")} AS pfeq,#{operators("c.conppeqop")} AS ppeq,
          #{operators("c.conffeqop")} AS ffeq,#{expr("c.conbin", "c.conrelid")} AS expression,
          c.conexclop IS NOT NULL AS excluded,c.confdelsetcols IS NOT NULL AS delete_columns
        FROM pg_catalog.pg_constraint c JOIN pg_catalog.pg_class r ON r.oid=c.conrelid JOIN pg_catalog.pg_namespace n ON n.oid=r.relnamespace
        LEFT JOIN pg_catalog.pg_class tr ON tr.oid=c.confrelid LEFT JOIN pg_catalog.pg_namespace tn ON tn.oid=tr.relnamespace
        WHERE c.conrelid IN(SELECT oid FROM targets) OR c.confrelid IN(SELECT oid FROM targets)
        ORDER BY c.oid LIMIT 110
        """

    {rows, state} = fetch!(state, sql, [ids], schema, 109, 109)
    demand(length(Enum.uniq(Enum.map(rows, & &1["oid"]))) == 109)

    demand(
      Enum.frequencies(Enum.map(rows, & &1["kind"])) === %{
        "c" => 80,
        "p" => 9,
        "u" => 4,
        "f" => 12,
        "t" => 4
      }
    )

    each!(rows, state, fn r ->
      trigger = r["kind"] == "t"

      demand(
        r["oid"] > 0 and r["local"] and r["validated"] and r["inherited"] == 0 and
          r["parent"] == 0 and r["domain"] == 0
      )

      demand(
        r["deferrable"] === trigger and r["deferred"] === trigger and
          r["noinherit"] === (r["kind"] != "c")
      )

      demand(not r["excluded"] and not r["delete_columns"])

      if r["kind"] != "f" do
        demand(
          r["target_oid"] == 0 and is_nil(r["target"]) and r["target_keys"] == [] and
            r["pfeq"] == [] and r["ppeq"] == [] and r["ffeq"] == []
        )

        demand(r["match"] == " " and r["update"] == " " and r["delete"] == " ")
      end

      if r["kind"] in ["c", "t"], do: demand(r["index"] == 0)
      if r["kind"] != "c", do: demand(is_nil(r["expression"]))
      if trigger, do: demand(r["keys"] == [])
    end)

    actual_checks =
      for r <- rows, r["kind"] == "c", do: {r["relation"], r["expression"], r["keys"]}

    expected_checks =
      for r <- manifest["check_keys"], do: {r["relation"], r["expression"], r["columns"]}

    demand(Enum.frequencies(actual_checks) === Enum.frequencies(expected_checks))

    each!(rows, state, fn r ->
      matching = Enum.filter(columns, &(&1["relation"] == r["relation"]))
      if matching != [], do: demand(Enum.all?(matching, &(&1["relid"] == r["relid"])))
    end)

    actual_keys =
      for r <- rows, r["kind"] in ["p", "u"], do: {r["relation"], r["kind"], r["keys"]}

    expected_keys =
      Enum.flat_map(manifest["structure"]["relations"], fn {rel, spec} ->
        [{rel, "p", spec["primary_key"]}] ++ Enum.map(spec["unique"], &{rel, "u", &1})
      end)

    demand(Enum.frequencies(actual_keys) === Enum.frequencies(expected_keys))

    expected_fks =
      Enum.flat_map(manifest["structure"]["relations"], fn {rel, spec} ->
        Enum.map(
          spec["foreign_keys"],
          &{rel, &1["columns"], &1["relation"], &1["referenced_columns"]}
        )
      end) ++
        Enum.map(
          manifest["structure"]["incoming_foreign_keys"],
          &{&1["source_relation"], &1["columns"], &1["relation"], &1["referenced_columns"]}
        )

    fks = Enum.filter(rows, &(&1["kind"] == "f"))

    demand(
      Enum.frequencies(
        Enum.map(fks, &{&1["relation"], &1["keys"], &1["target"], &1["target_keys"]})
      ) === Enum.frequencies(expected_fks)
    )

    each!(fks, state, fn r ->
      demand(r["match"] == "s" and r["update"] == "a" and r["delete"] == "a" and r["index"] > 0)

      eqs =
        Enum.map(r["target_keys"], fn key ->
          c = Enum.find(columns, &(&1["relid"] == r["target_oid"] and &1["name"] == key))
          demand(not is_nil(c))
          "pg_catalog.=:" <> c["type"] <> ":" <> c["type"]
        end)

      demand(r["pfeq"] === eqs and r["ppeq"] === eqs and r["ffeq"] === eqs)

      demand(
        Enum.all?(columns, fn c -> c["relation"] != r["relation"] or c["relid"] == r["relid"] end)
      )
    end)

    {rows, state}
  end

  defp bounded_array(array, select) do
    "CASE WHEN pg_catalog.cardinality(#{array})>32 THEN ARRAY['#{@marker}']::pg_catalog.text[] ELSE ARRAY(#{select}) END"
  end

  defp indexes!(state, ids, columns, constraints, manifest, roles) do
    schema = [
      {"oid", :oid},
      {"relid", :oid},
      {"relation", {:text, 127}},
      {"name", {:text, 63}},
      {"namespace", {:text, 63}},
      {"owner", :oid},
      {"method", {:text, 63}},
      {"natts", :int},
      {"nkeys", :int},
      {"unique", :bool},
      {"primary", :bool},
      {"nulls", :bool},
      {"exclusion", :bool},
      {"immediate", :bool},
      {"clustered", :bool},
      {"valid", :bool},
      {"xmin", :bool},
      {"ready", :bool},
      {"live", :bool},
      {"replica", :bool},
      {"keys", {:array, {:text, 63}, 32}},
      {"opclasses", {:array, {:text, 256}, 32}},
      {"collations", {:array, {:nullable, {:text, 127}}, 32}},
      {"collation_oids", {:array, :oid, 32}},
      {"options", {:array, :int, 32}},
      {"expression", {:nullable, {:text, 8192}}},
      {"predicate", {:nullable, {:text, 8192}}},
      {"kind", {:text, 1}},
      {"partition", :bool},
      {"persistence", {:text, 1}},
      {"inheritance", :bool}
    ]

    ops =
      bounded_array(
        "i.indclass::pg_catalog.oid[]",
        "SELECT n.nspname::pg_catalog.text||'.'||o.opcname::pg_catalog.text||':'||tn.nspname::pg_catalog.text||'.'||t.typname::pg_catalog.text||':'||fn.nspname::pg_catalog.text||'.'||f.opfname::pg_catalog.text FROM pg_catalog.unnest(i.indclass::pg_catalog.oid[]) WITH ORDINALITY k(id,ord) LEFT JOIN pg_catalog.pg_opclass o ON o.oid=k.id LEFT JOIN pg_catalog.pg_namespace n ON n.oid=o.opcnamespace LEFT JOIN pg_catalog.pg_type t ON t.oid=o.opcintype LEFT JOIN pg_catalog.pg_namespace tn ON tn.oid=t.typnamespace LEFT JOIN pg_catalog.pg_opfamily f ON f.oid=o.opcfamily LEFT JOIN pg_catalog.pg_namespace fn ON fn.oid=f.opfnamespace WHERE o.opcmethod=c.relam AND f.opfmethod=c.relam ORDER BY k.ord"
      )

    colls =
      bounded_array(
        "i.indcollation::pg_catalog.oid[]",
        "SELECT CASE WHEN k.id=0 THEN NULL ELSE n.nspname::pg_catalog.text||'.'||c.collname::pg_catalog.text END FROM pg_catalog.unnest(i.indcollation::pg_catalog.oid[]) WITH ORDINALITY k(id,ord) LEFT JOIN pg_catalog.pg_collation c ON c.oid=k.id LEFT JOIN pg_catalog.pg_namespace n ON n.oid=c.collnamespace ORDER BY k.ord"
      )

    sql =
      names_cte() <>
        """
        SELECT i.indexrelid::pg_catalog.int8 AS oid,i.indrelid::pg_catalog.int8 AS relid,x.name AS relation,
          c.relname::pg_catalog.text AS name,n.nspname::pg_catalog.text AS namespace,c.relowner::pg_catalog.int8 AS owner,
          am.amname::pg_catalog.text AS method,i.indnatts::pg_catalog.int4 AS natts,i.indnkeyatts::pg_catalog.int4 AS nkeys,
          i.indisunique AS unique,i.indisprimary AS primary,i.indnullsnotdistinct AS nulls,i.indisexclusion AS exclusion,
          i.indimmediate AS immediate,i.indisclustered AS clustered,i.indisvalid AS valid,i.indcheckxmin AS xmin,
          i.indisready AS ready,i.indislive AS live,i.indisreplident AS replica,
          #{key_names("i.indkey::pg_catalog.int2[]", "i.indrelid")} AS keys,#{ops} AS opclasses,#{colls} AS collations,
        CASE WHEN pg_catalog.cardinality(i.indcollation::pg_catalog.oid[])>32 THEN ARRAY[4294967295]::pg_catalog.oid[] ELSE i.indcollation::pg_catalog.oid[] END AS collation_oids,
          CASE WHEN pg_catalog.cardinality(i.indoption::pg_catalog.int2[])>32 THEN ARRAY[-1]::pg_catalog.int2[] ELSE i.indoption::pg_catalog.int2[] END AS options,
          #{expr("i.indexprs", "i.indrelid")} AS expression,#{expr("i.indpred", "i.indrelid")} AS predicate,
          c.relkind::pg_catalog.text AS kind,c.relispartition AS partition,c.relpersistence::pg_catalog.text AS persistence,
          EXISTS(SELECT 1 FROM pg_catalog.pg_inherits h WHERE h.inhrelid=c.oid OR h.inhparent=c.oid) AS inheritance
        FROM targets x JOIN pg_catalog.pg_index i ON i.indrelid=x.oid JOIN pg_catalog.pg_class c ON c.oid=i.indexrelid
        JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace JOIN pg_catalog.pg_am am ON am.oid=c.relam
        ORDER BY i.indexrelid LIMIT 15
        """

    {rows, state} = fetch!(state, sql, [ids], schema, 14, 14)
    demand(length(Enum.uniq(Enum.map(rows, & &1["oid"]))) == 14)

    each!(rows, state, fn r ->
      demand(
        r["oid"] > 0 and r["owner"] == roles.relation_owner and r["namespace"] == "public" and
          r["method"] == "btree"
      )

      demand(
        r["natts"] == length(r["keys"]) and r["nkeys"] == r["natts"] and r["unique"] and
          r["immediate"] and r["valid"] and r["ready"] and r["live"]
      )

      demand(
        not Enum.any?(~w(nulls exclusion clustered xmin replica partition inheritance), &r[&1])
      )

      demand(
        r["kind"] == "i" and r["persistence"] == "p" and is_nil(r["expression"]) and
          r["options"] === List.duplicate(0, r["nkeys"])
      )

      keycols =
        Enum.map(r["keys"], fn key ->
          Enum.find(columns, &(&1["relid"] == r["relid"] and &1["name"] == key))
        end)

      demand(Enum.all?(keycols, &is_map/1))

      opclasses =
        Enum.map(keycols, fn c ->
          type = String.replace_prefix(c["type"], "pg_catalog.", "")
          family = if type in ["int4", "int8"], do: "integer_ops", else: type <> "_ops"
          "pg_catalog." <> type <> "_ops:" <> c["type"] <> ":pg_catalog." <> family
        end)

      demand(
        r["opclasses"] === opclasses and r["collations"] === Enum.map(keycols, & &1["collation"]) and
          r["collation_oids"] === Enum.map(keycols, & &1["collation_oid"])
      )

      backing = Enum.filter(constraints, &(&1["kind"] in ["p", "u"] and &1["index"] == r["oid"]))

      if is_nil(r["predicate"]) do
        demand(length(backing) == 1)
        [c] = backing

        demand(
          c["relid"] == r["relid"] and c["keys"] === r["keys"] and
            r["primary"] === (c["kind"] == "p")
        )
      else
        demand(
          backing == [] and r["name"] == "mixer_browser_one_attempt" and
            r["relation"] == "public.mixer_browser_oidc_attempts"
        )

        demand(r["keys"] === ["browser_id", "browser_epoch"] and not r["primary"])
        [expected] = manifest["expressions"]["predicates"]
        demand(r["predicate"] === expected["expression"])
      end
    end)

    demand(Enum.count(rows, &(not is_nil(&1["predicate"]))) == 1)

    each!(Enum.filter(constraints, &(&1["kind"] in ["p", "u", "f"])), state, fn c ->
      i = Enum.find(rows, &(&1["oid"] == c["index"]))
      demand(is_map(i))
      demand(i["relid"] === if(c["kind"] == "f", do: c["target_oid"], else: c["relid"]))
      demand(i["keys"] === if(c["kind"] == "f", do: c["target_keys"], else: c["keys"]))
      demand(is_nil(i["predicate"]))
    end)

    {rows, state}
  end

  defp triggers!(state, ids, constraints, indexes, manifest, roles) do
    schema = [
      {"oid", :oid},
      {"relid", :oid},
      {"relation", {:text, 127}},
      {"name", {:text, 63}},
      {"internal", :bool},
      {"events", :int},
      {"enabled", {:text, 1}},
      {"function_oid", :oid},
      {"function", {:text, 127}},
      {"nargs", :int},
      {"result", {:text, 127}},
      {"language", {:text, 63}},
      {"function_owner", :oid},
      {"definer", :bool},
      {"source", {:nullable, {:text, 65536}}},
      {"settings", {:nullable, {:array, {:text, 256}, 32}}},
      {"function_acl", :bool},
      {"deferrable", :bool},
      {"deferred", :bool},
      {"arguments", :int},
      {"args", {:text, 8192}},
      {"columns", {:array, :int, 32}},
      {"qual", {:nullable, {:text, 8192}}},
      {"old", {:nullable, {:text, 63}}},
      {"new", {:nullable, {:text, 63}}},
      {"parent", :oid},
      {"opposite", :oid},
      {"index", :oid},
      {"constraint", :oid}
    ]

    sql =
      names_cte() <>
        """
        SELECT t.oid::pg_catalog.int8 AS oid,t.tgrelid::pg_catalog.int8 AS relid,n.nspname::pg_catalog.text||'.'||c.relname::pg_catalog.text AS relation,
          t.tgname::pg_catalog.text AS name,t.tgisinternal AS internal,t.tgtype::pg_catalog.int4 AS events,t.tgenabled::pg_catalog.text AS enabled,
          p.oid::pg_catalog.int8 AS function_oid,pn.nspname::pg_catalog.text||'.'||p.proname::pg_catalog.text AS function,
          p.pronargs::pg_catalog.int4 AS nargs,tn.nspname::pg_catalog.text||'.'||rt.typname::pg_catalog.text AS result,
          l.lanname::pg_catalog.text AS language,p.proowner::pg_catalog.int8 AS function_owner,p.prosecdef AS definer,
          CASE WHEN t.tgisinternal THEN NULL WHEN pg_catalog.octet_length(p.prosrc)>65536 THEN '#{@marker}' ELSE p.prosrc END AS source,
          CASE WHEN pg_catalog.cardinality(p.proconfig)>32 OR pg_catalog.octet_length(p.proconfig::pg_catalog.text)>8192 THEN ARRAY['#{@marker}']::pg_catalog.text[] ELSE p.proconfig END AS settings,
          CASE WHEN t.tgisinternal THEN true WHEN NOT #{acl_ok("p.proacl")} THEN false ELSE
            NOT EXISTS(SELECT 1 FROM pg_catalog.aclexplode(COALESCE(p.proacl,pg_catalog.acldefault('f',p.proowner))) a
              WHERE a.grantee<>$2::pg_catalog.oid OR a.grantor<>$2::pg_catalog.oid OR a.privilege_type<>'EXECUTE' OR a.is_grantable)
            AND NOT pg_catalog.has_function_privilege($3::pg_catalog.oid,p.oid,'EXECUTE')
            AND NOT pg_catalog.has_function_privilege($4::pg_catalog.oid,p.oid,'EXECUTE') END AS function_acl,
          t.tgdeferrable AS deferrable,t.tginitdeferred AS deferred,t.tgnargs::pg_catalog.int4 AS arguments,
          CASE WHEN pg_catalog.octet_length(t.tgargs)>4096 THEN '#{@marker}' ELSE pg_catalog.encode(t.tgargs,'hex') END AS args,
          CASE WHEN pg_catalog.cardinality(t.tgattr::pg_catalog.int2[])>32 THEN ARRAY[-1]::pg_catalog.int2[] ELSE t.tgattr::pg_catalog.int2[] END AS columns,
          #{expr("t.tgqual", "t.tgrelid")} AS qual,t.tgoldtable::pg_catalog.text AS old,t.tgnewtable::pg_catalog.text AS new,
          t.tgparentid::pg_catalog.int8 AS parent,t.tgconstrrelid::pg_catalog.int8 AS opposite,t.tgconstrindid::pg_catalog.int8 AS index,t.tgconstraint::pg_catalog.int8 AS constraint
        FROM pg_catalog.pg_trigger t JOIN pg_catalog.pg_class c ON c.oid=t.tgrelid JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
        JOIN pg_catalog.pg_proc p ON p.oid=t.tgfoid AND p.prokind='f'
        JOIN pg_catalog.pg_namespace pn ON pn.oid=p.pronamespace JOIN pg_catalog.pg_type rt ON rt.oid=p.prorettype
        JOIN pg_catalog.pg_namespace tn ON tn.oid=rt.typnamespace JOIN pg_catalog.pg_language l ON l.oid=p.prolang
        WHERE t.tgrelid IN(SELECT oid FROM targets) OR t.tgconstraint IN(
          SELECT k.oid FROM pg_catalog.pg_constraint k WHERE k.conrelid IN(SELECT oid FROM targets) OR k.confrelid IN(SELECT oid FROM targets))
        ORDER BY t.oid LIMIT 54
        """

    {rows, state} =
      fetch!(
        state,
        sql,
        [ids, roles.writer, roles.lifecycle_login, roles.ordinary_runtime_login],
        schema,
        53,
        53
      )

    demand(length(Enum.uniq(Enum.map(rows, & &1["oid"]))) == 53)

    each!(rows, state, fn t ->
      demand(
        t["oid"] > 0 and t["function_oid"] > 0 and t["enabled"] == "O" and t["nargs"] == 0 and
          t["result"] == "pg_catalog.trigger"
      )

      demand(
        t["arguments"] == 0 and t["args"] == "" and t["columns"] == [] and is_nil(t["qual"]) and
          is_nil(t["old"]) and is_nil(t["new"]) and t["parent"] == 0
      )
    end)

    ri = Enum.filter(rows, & &1["internal"])
    demand(length(ri) == 48)

    funcs = %{
      "pg_catalog.RI_FKey_check_ins" => {5, :child},
      "pg_catalog.RI_FKey_check_upd" => {17, :child},
      "pg_catalog.RI_FKey_noaction_del" => {9, :parent},
      "pg_catalog.RI_FKey_noaction_upd" => {17, :parent}
    }

    each!(Enum.filter(constraints, &(&1["kind"] == "f")), state, fn c ->
      group = Enum.filter(ri, &(&1["constraint"] == c["oid"]))

      demand(
        Enum.frequencies(Enum.map(group, & &1["function"])) === Map.new(Map.keys(funcs), &{&1, 1})
      )

      each!(group, state, fn t ->
        {events, side} = Map.fetch!(funcs, t["function"])

        demand(
          t["events"] == events and not t["deferrable"] and not t["deferred"] and
            t["language"] == "internal"
        )

        demand(t["relid"] == if(side == :child, do: c["relid"], else: c["target_oid"]))
        demand(t["opposite"] == if(side == :child, do: c["target_oid"], else: c["relid"]))
        demand(t["index"] == c["index"] and Enum.any?(indexes, &(&1["oid"] == t["index"])))
      end)
    end)

    user = Enum.reject(rows, & &1["internal"])
    demand(length(user) == 5)
    expected = manifest["structure"]["user_triggers"]

    demand(
      Enum.frequencies(Enum.map(user, &{&1["relation"], &1["name"]})) ===
        Enum.frequencies(Enum.map(expected, &{&1["relation"], &1["name"]}))
    )

    each!(user, state, fn t ->
      e = Enum.find(expected, &(&1["relation"] == t["relation"] and &1["name"] == t["name"]))
      function = String.trim_trailing(e["function"], "()")

      demand(
        t["function"] === function and
          t["source"] ===
            manifest["trigger_sources"][String.replace_prefix(function, "public.", "")]
      )

      demand(
        t["language"] == "plpgsql" and t["definer"] and t["function_owner"] == roles.writer and
          t["function_acl"]
      )

      demand(Enum.sort(t["settings"]) === Enum.sort(@function_settings))

      events =
        if e["name"] == "mixer_browser_immutable",
          do: 27,
          else: if(e["events"] == ["INSERT"], do: 5, else: 21)

      demand(
        t["events"] == events and t["deferrable"] === e["deferrable"] and
          t["deferred"] === e["initially_deferred"]
      )

      demand(t["opposite"] == 0 and t["index"] == 0)

      if e["constraint"] do
        c = Enum.find(constraints, &(&1["oid"] == t["constraint"]))
        demand(is_map(c) and c["kind"] == "t" and c["relid"] == t["relid"])
      else
        demand(t["constraint"] == 0)
      end
    end)

    demand(
      length(Enum.uniq(Enum.map(Enum.filter(user, &(&1["constraint"] > 0)), & &1["constraint"]))) ==
        4
    )

    each!(Enum.group_by(rows, & &1["function"]), state, fn {_, ts} ->
      demand(length(Enum.uniq(Enum.map(ts, & &1["function_oid"]))) == 1)
    end)

    {rows, state}
  end

  defp policies!(state, ids, manifest, roles) do
    schema = [
      {"relation", {:text, 127}},
      {"name", {:text, 63}},
      {"command", {:text, 1}},
      {"permissive", :bool},
      {"roles", {:array, :oid, 4}},
      {"using", {:nullable, {:text, 8192}}},
      {"check", {:nullable, {:text, 8192}}}
    ]

    sql =
      names_cte() <>
        """
        SELECT x.name AS relation,p.polname::pg_catalog.text AS name,p.polcmd::pg_catalog.text AS command,p.polpermissive AS permissive,
          CASE WHEN pg_catalog.cardinality(p.polroles)>4 THEN ARRAY[4294967295]::pg_catalog.oid[] ELSE p.polroles END AS roles,
          #{expr("p.polqual", "p.polrelid")} AS using,#{expr("p.polwithcheck", "p.polrelid")} AS check
        FROM targets x JOIN pg_catalog.pg_policy p ON p.polrelid=x.oid ORDER BY p.oid LIMIT 33
        """

    {rows, state} = fetch!(state, sql, [ids], schema, 32, 32)
    commands = %{"SELECT" => "r", "INSERT" => "a", "UPDATE" => "w", "DELETE" => "d", "ALL" => "*"}

    expected =
      Enum.flat_map(manifest["structure"]["policies"], fn {rel, ps} ->
        Enum.map(ps, fn p ->
          e =
            Enum.find(
              manifest["expressions"]["policies"],
              &(&1["relation"] == rel and &1["polname"] == p["name"])
            )

          %{
            "relation" => rel,
            "name" => p["name"],
            "command" => commands[p["command"]],
            "permissive" => p["permissive"],
            "roles" => if(p["roles"] == ["PUBLIC"], do: [0], else: [roles.writer]),
            "using" => e["using_expr"],
            "check" => e["check_expr"]
          }
        end)
      end)

    demand(Enum.frequencies(rows) === Enum.frequencies(expected))
    {rows, state}
  end

  defp table_tokens(16), do: ~w(SELECT INSERT UPDATE DELETE TRUNCATE REFERENCES TRIGGER)
  defp table_tokens(17), do: ~w(SELECT INSERT UPDATE DELETE TRUNCATE REFERENCES TRIGGER MAINTAIN)
  defp apps(roles), do: [roles.lifecycle_login, roles.writer, roles.ordinary_runtime_login]

  defp privileges!(state, ids, columns, manifest, roles, major) do
    schema = [
      {"relation", {:text, 127}},
      {"column", {:nullable, {:text, 63}}},
      {"null", :bool},
      {"grantee", :oid},
      {"grantor", :oid},
      {"privilege", {:text, 16}},
      {"option", :bool}
    ]

    sql =
      names_cte() <>
        """
        SELECT q.relation,q.column,q.null,q.grantee,q.grantor,q.privilege,q.option FROM (
          SELECT x.name AS relation,NULL::pg_catalog.text AS column,c.relacl IS NULL AS null,
            a.grantee::pg_catalog.int8 AS grantee,a.grantor::pg_catalog.int8 AS grantor,a.privilege_type::pg_catalog.text AS privilege,a.is_grantable AS option
          FROM targets x JOIN pg_catalog.pg_class c ON c.oid=x.oid
          CROSS JOIN LATERAL pg_catalog.aclexplode(CASE WHEN #{acl_ok("c.relacl")} THEN COALESCE(c.relacl,pg_catalog.acldefault('r',c.relowner)) ELSE NULL::pg_catalog.aclitem[] END) a
          UNION ALL
          SELECT x.name,a.attname::pg_catalog.text,false,e.grantee::pg_catalog.int8,e.grantor::pg_catalog.int8,e.privilege_type::pg_catalog.text,e.is_grantable
          FROM targets x JOIN pg_catalog.pg_attribute a ON a.attrelid=x.oid
          CROSS JOIN LATERAL pg_catalog.aclexplode(CASE WHEN #{acl_ok("a.attacl")} THEN a.attacl ELSE NULL::pg_catalog.aclitem[] END) e
          WHERE a.attnum>0
        ) q ORDER BY q.relation,q.column,q.grantee,q.privilege LIMIT 513
        """

    expected =
      Enum.flat_map(manifest["structure"]["writer_grants"], fn {rel, g} ->
        base =
          Enum.map(
            table_tokens(major),
            &acl_row(rel, nil, roles.relation_owner, roles.relation_owner, &1)
          )

        writer = Enum.map(g["table"], &acl_row(rel, nil, roles.writer, roles.relation_owner, &1))

        mutable =
          Enum.map(
            g["update_columns"],
            &acl_row(rel, &1, roles.writer, roles.relation_owner, "UPDATE")
          )

        ordinary =
          if String.starts_with?(rel, "public.mixer_authz_"),
            do: [acl_row(rel, nil, roles.ordinary_runtime_login, roles.relation_owner, "SELECT")],
            else: []

        base ++ writer ++ mutable ++ ordinary
      end)

    {rows, state} = fetch!(state, sql, [ids], schema, 512, length(expected))
    demand(Enum.frequencies(rows) === Enum.frequencies(expected))
    tokens = table_tokens(major)

    effective_sql =
      Enum.map_join(tokens, ",", fn token ->
        "pg_catalog.has_table_privilege(r.role,x.oid,'#{token}')"
      end)

    schema = [{"role", :oid}, {"relation", {:text, 127}}, {"rights", {:array, :bool, 8}}]

    sql =
      names_cte() <>
        """
        SELECT r.role::pg_catalog.int8 AS role,x.name AS relation,ARRAY[#{effective_sql}] AS rights
        FROM pg_catalog.unnest($2::pg_catalog.oid[]) r(role) CROSS JOIN targets x ORDER BY r.role,x.oid LIMIT 28
        """

    {tables, state} = fetch!(state, sql, [ids, apps(roles)], schema, 27, 27)

    each!(tables, state, fn r ->
      expected =
        Enum.map(tokens, fn privilege ->
          grants = manifest["structure"]["writer_grants"][r["relation"]]

          cond do
            r["role"] == roles.writer ->
              privilege in grants["table"]

            r["role"] == roles.ordinary_runtime_login ->
              privilege == "SELECT" and String.starts_with?(r["relation"], "public.mixer_authz_")

            r["role"] == roles.lifecycle_login ->
              false

            true ->
              raise Unavailable
          end
        end)

      demand(r["rights"] === expected)
    end)

    demand(length(Enum.uniq(Enum.map(tables, &{&1["role"], &1["relation"]}))) == 27)

    checks =
      Enum.map_join(~w(SELECT INSERT UPDATE REFERENCES), ",", fn token ->
        "pg_catalog.has_column_privilege(r.role,a.attrelid,a.attnum,'#{token}')"
      end)

    schema = [{"role", :oid}, {"relid", :oid}, {"number", :int}, {"rights", {:array, :bool, 4}}]

    sql =
      names_cte() <>
        """
        SELECT r.role::pg_catalog.int8 AS role,a.attrelid::pg_catalog.int8 AS relid,a.attnum::pg_catalog.int4 AS number,ARRAY[#{checks}] AS rights
        FROM pg_catalog.unnest($2::pg_catalog.oid[]) r(role) CROSS JOIN targets x
        JOIN pg_catalog.pg_attribute a ON a.attrelid=x.oid WHERE a.attnum>0 ORDER BY r.role,a.attrelid,a.attnum LIMIT 373
        """

    {cols, state} = fetch!(state, sql, [ids, apps(roles)], schema, 372, 372)

    each!(cols, state, fn r ->
      c = Enum.find(columns, &(&1["relid"] == r["relid"] and &1["number"] == r["number"]))
      demand(is_map(c))
      g = manifest["structure"]["writer_grants"][c["relation"]]

      expected =
        cond do
          r["role"] == roles.writer ->
            [
              "SELECT" in g["table"],
              "INSERT" in g["table"],
              c["name"] in g["update_columns"],
              false
            ]

          r["role"] == roles.ordinary_runtime_login ->
            [String.starts_with?(c["relation"], "public.mixer_authz_"), false, false, false]

          r["role"] == roles.lifecycle_login ->
            [false, false, false, false]

          true ->
            raise Unavailable
        end

      demand(r["rights"] === expected)
    end)

    demand(length(Enum.uniq(Enum.map(cols, &{&1["role"], &1["relid"], &1["number"]}))) == 372)
    {rows, state}
  end

  defp acl_row(rel, column, grantee, grantor, privilege),
    do: %{
      "relation" => rel,
      "column" => column,
      "null" => false,
      "grantee" => grantee,
      "grantor" => grantor,
      "privilege" => privilege,
      "option" => false
    }

  defp forbidden!(state, ids, roles, major) do
    # Fixed EXISTS deny all writer/lifecycle rights outside the exact nine,
    # including column-only grants and writable views/foreign relations. Function,
    # type and complete role-topology checks remain separate prerequisites.
    tests =
      Enum.map_join(table_tokens(major), " OR ", fn token ->
        "pg_catalog.has_table_privilege(r.role,c.oid,'#{token}')"
      end)

    columns =
      Enum.map_join(~w(SELECT INSERT UPDATE REFERENCES), " OR ", fn token ->
        "pg_catalog.has_any_column_privilege(r.role,c.oid,'#{token}')"
      end)

    sql =
      names_cte() <>
        """
        SELECT 1::pg_catalog.int4 AS forbidden WHERE
          EXISTS(SELECT 1 FROM pg_catalog.pg_inherits h WHERE h.inhrelid IN(SELECT oid FROM targets) OR h.inhparent IN(SELECT oid FROM targets))
          OR EXISTS(SELECT 1 FROM pg_catalog.pg_rewrite w WHERE w.ev_class IN(SELECT oid FROM targets))
          OR EXISTS(SELECT 1 FROM pg_catalog.pg_foreign_table f WHERE f.ftrelid IN(SELECT oid FROM targets))
          OR EXISTS(SELECT 1 FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
            CROSS JOIN pg_catalog.unnest($2::pg_catalog.oid[]) r(role)
            WHERE n.nspname<>'information_schema' AND pg_catalog.left(n.nspname::pg_catalog.text,3)<>'pg_'
              AND c.relkind IN('r','p','v','m','f','S') AND c.oid NOT IN(SELECT oid FROM targets)
              AND (c.relowner=r.role OR CASE WHEN c.relkind='S' THEN
                pg_catalog.has_sequence_privilege(r.role,c.oid,'SELECT') OR pg_catalog.has_sequence_privilege(r.role,c.oid,'UPDATE') OR pg_catalog.has_sequence_privilege(r.role,c.oid,'USAGE')
                ELSE (#{tests}) OR (#{columns}) END))
          OR EXISTS(SELECT 1 FROM pg_catalog.pg_namespace n CROSS JOIN pg_catalog.unnest($2::pg_catalog.oid[]) r(role)
            WHERE n.nspowner=r.role OR pg_catalog.has_schema_privilege(r.role,n.oid,'CREATE'))
        LIMIT 1
        """

    fetch!(state, sql, [ids, [roles.writer, roles.lifecycle_login]], [{"forbidden", :int}], 0, 0)
  end
end
