defmodule MixerHosted.Builds.OperationIntentSchema do
  @moduledoc false

  @entry "public.mixer_build_operation_intent_v1(text,text,bytea,bytea,bigint,uuid,bigint,bigint,text,timestamp with time zone,jsonb,jsonb)"
  @owner_primitives [
    "public.mixer_build_operation_admit(text,text,bytea,bytea,bigint,uuid,bigint,bigint,text,timestamp with time zone)",
    "public.mixer_build_operation_admissions_immutable()"
  ]
  @schema_path Path.expand("../../../priv/unselected_operation_admission", __DIR__)
  @external_resource Path.join(@schema_path, "05_processor_intent_body.sql")
  @external_resource Path.join(@schema_path, "04_admission_function.sql")
  @external_resource Path.join(@schema_path, "02_immutable_function.sql")
  @body File.read!(Path.join(@schema_path, "05_processor_intent_body.sql"))
  @primitives Enum.map(~w(04_admission_function.sql 02_immutable_function.sql), fn file ->
                File.read!(Path.join(@schema_path, file)) |> String.split("$$") |> Enum.at(1)
              end)
  @arguments ~w(p_action p_id p_ref p_spec p_deadline p_record p_epoch p_revision p_owner p_expires p_ref_scope p_spec_scope outcome admission_state lease_epoch journal_revision)
  @result "TABLE(outcome text, admission_state text, lease_epoch bigint, journal_revision bigint)"

  def entry, do: @entry

  # Browser admission accepts either ACL with the installed builds profile.
  # Processor admission requires the exact ACL for its explicit runtime mode.
  def compatible?(query, mode) when mode in [:optional, :disabled, :required] do
    query.(
      """
      WITH expected(signature, body) AS (
        SELECT * FROM unnest($1::text[], $2::text[])
      ), owner AS (
        SELECT oid FROM pg_roles WHERE rolname='browser_schema_owner'
          AND NOT (rolcanlogin OR rolsuper OR rolbypassrls)
      ), entry AS (
        SELECT p.* FROM pg_proc p WHERE p.oid=to_regprocedure($3)
      ), relation AS (
        SELECT c.* FROM pg_class c WHERE c.oid=to_regclass('public.mixer_build_operation_admissions')
      )
      SELECT NOT EXISTS (
        SELECT 1 FROM relation c
        WHERE c.relrowsecurity OR c.relforcerowsecurity
          OR EXISTS (SELECT 1 FROM pg_policy p WHERE p.polrelid=c.oid)
      ) AND CASE WHEN NOT EXISTS (SELECT 1 FROM entry) THEN
        $4 <> 'required' AND NOT EXISTS (
          SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
          WHERE n.nspname='public' AND p.proname='mixer_build_operation_intent_v1'
        )
      ELSE
        (SELECT count(*)=1 AND bool_and(
          p.proowner=(SELECT oid FROM owner) AND p.prosrc=$5 AND p.prosecdef
          AND p.proconfig=ARRAY['search_path=pg_catalog, public, pg_temp']::text[]
          AND p.proargnames=$6::text[] AND pg_get_function_result(p.oid)=$7
          AND p.prokind='f' AND p.provolatile='v' AND p.proparallel='u'
          AND p.proretset AND NOT p.proisstrict AND NOT p.proleakproof
          AND p.pronargdefaults=0 AND p.prosupport=0 AND p.provariadic=0
          AND p.probin IS NULL AND p.prosqlbody IS NULL
          AND p.prolang=(SELECT oid FROM pg_language WHERE lanname='plpgsql')
          AND (SELECT count(*) FROM pg_proc sibling WHERE sibling.pronamespace=p.pronamespace
               AND sibling.proname=p.proname)=1
          AND NOT EXISTS (
            SELECT 1 FROM aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a
            WHERE a.grantor<>p.proowner OR a.privilege_type<>'EXECUTE' OR a.is_grantable
              OR (a.grantee<>p.proowner AND ($4='disabled'
                OR a.grantee<>coalesce((SELECT oid FROM pg_roles WHERE rolname=$8),0) OR a.grantee=0))
          )
          AND has_function_privilege(p.proowner,p.oid,'EXECUTE')
          AND ($4<>'required' OR EXISTS (
            SELECT 1 FROM aclexplode(p.proacl) a JOIN pg_roles r ON r.oid=a.grantee
            WHERE r.rolname=$8 AND a.grantor=p.proowner AND a.privilege_type='EXECUTE'
              AND NOT a.is_grantable
          ))
        ) FROM entry p)
        AND (SELECT count(*)=2 AND bool_and(p.proowner=(SELECT oid FROM owner)
           AND p.prosrc=e.body AND NOT p.prosecdef AND p.proconfig IS NULL
           AND p.prolang=(SELECT oid FROM pg_language WHERE lanname='plpgsql')
           AND has_function_privilege(p.proowner,p.oid,'EXECUTE')
           AND NOT EXISTS (
             SELECT 1 FROM aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a
             WHERE a.grantee<>p.proowner OR a.grantor<>p.proowner OR a.privilege_type<>'EXECUTE'
               OR a.is_grantable
           )) FROM expected e JOIN pg_proc p ON p.oid=to_regprocedure(e.signature))
        AND (SELECT count(*)=1 AND bool_and(c.relowner=(SELECT oid FROM owner) AND c.relkind='r'
           AND NOT EXISTS (SELECT 1 FROM aclexplode(c.relacl) a WHERE a.grantee<>c.relowner)
           AND NOT EXISTS (SELECT 1 FROM pg_attribute t CROSS JOIN LATERAL aclexplode(t.attacl) a
                           WHERE t.attrelid=c.oid AND a.grantee<>c.relowner)
           AND EXISTS (SELECT 1 FROM pg_trigger t WHERE t.tgrelid=c.oid AND NOT t.tgisinternal
                       AND t.tgfoid=to_regprocedure(($1::text[])[2])
                       AND t.tgtype=27 AND t.tgenabled='O' AND t.tgqual IS NULL AND t.tgnargs=0)
        ) FROM relation c)
      END
      """,
      [
        @owner_primitives,
        @primitives,
        @entry,
        Atom.to_string(mode),
        @body,
        @arguments,
        @result,
        MixerHosted.Builds.ProcessorProfile.role()
      ]
    ) == [[true]]
  end
end
