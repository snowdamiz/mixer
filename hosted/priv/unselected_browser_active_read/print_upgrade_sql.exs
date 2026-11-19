alias MixerHosted.BrowserAuth.ActiveReadSchema

# Pin both admitted bodies so a later schema change cannot silently change this upgrade.
exclusive = "9f0a73cba023bd61e7908fbf62ea7126a049e8976a8088df3f557fc787e57a47"
shared = "706d47a9d9453876630ecb2561614f64b007002a7c3ee92611245108425b1d3e"

{from, to, mode} =
  case System.argv() do
    ["up"] -> {exclusive, shared, :read}
    ["down"] -> {shared, exclusive, :create}
    _ -> raise ArgumentError, "expected up or down"
  end

ddl =
  ActiveReadSchema.function(mode)
  |> String.replace_prefix("CREATE FUNCTION ", "CREATE OR REPLACE FUNCTION ")

[header, body] = String.split(ddl, "\nAS $active_read$\n", parts: 2)
[definition, _settings] = String.split(header, "\nSET ", parts: 2)

IO.write("""
BEGIN;
SET LOCAL search_path = pg_catalog;
SET LOCAL statement_timeout = '5s';
SET LOCAL lock_timeout = '500ms';

DO $active_read_upgrade$
DECLARE
  target regprocedure := to_regprocedure(
    'public.mixer_browser_current_active_load(bytea,bytea,bigint,public.mixer_browser_access_evidence)'
  );
  writer pg_roles;
  lifecycle oid := to_regrole('browser_lifecycle')::oid;
  prior pg_proc;
  replaced pg_proc;
  settings_clauses text;
BEGIN
  SELECT * INTO STRICT prior FROM pg_proc WHERE oid = target FOR UPDATE;
  SELECT * INTO STRICT writer FROM pg_roles WHERE rolname = 'browser_writer';

  IF writer.rolcanlogin OR writer.rolinherit OR writer.rolsuper OR writer.rolbypassrls
    OR writer.rolcreaterole OR writer.rolcreatedb OR writer.rolreplication
    OR EXISTS (SELECT 1 FROM pg_auth_members WHERE member = writer.oid OR roleid = writer.oid)
  THEN
    RAISE EXCEPTION 'active-load function has an unexpected writer role';
  END IF;

  IF prior.proowner IS DISTINCT FROM writer.oid
    OR NOT prior.prosecdef
    OR encode(sha256(convert_to(prior.prosrc, 'UTF8')), 'hex') <> '#{from}'
  THEN
    RAISE EXCEPTION 'active-load function has an unexpected definition';
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM aclexplode(COALESCE(prior.proacl, acldefault('f', prior.proowner))) acl
    HAVING count(*) = 2
      AND count(*) FILTER (WHERE acl.grantee = writer.oid) = 1
      AND count(*) FILTER (WHERE acl.grantee = lifecycle) = 1
      AND bool_and(acl.grantor = writer.oid AND acl.privilege_type = 'EXECUTE' AND NOT acl.is_grantable)
  ) THEN
    RAISE EXCEPTION 'active-load function has an unexpected ACL';
  END IF;

  IF cardinality(prior.proconfig) IS DISTINCT FROM 5
    OR (SELECT array_agg(setting ORDER BY setting COLLATE "C") FROM unnest(prior.proconfig) AS config(setting))
      IS DISTINCT FROM ARRAY['bytea_output=hex', 'idle_in_transaction_session_timeout=5s',
        'lock_timeout=500ms', 'search_path=pg_catalog', 'statement_timeout=5s']
  THEN
    RAISE EXCEPTION 'active-load function has unexpected settings';
  END IF;

  -- Runtime admits any order of these settings. Keep the existing catalog order.
  SELECT string_agg(format('SET %I TO %L', split_part(setting, '=', 1), split_part(setting, '=', 2)),
    chr(10) ORDER BY ordinal)
  INTO settings_clauses
  FROM unnest(prior.proconfig) WITH ORDINALITY AS config(setting, ordinal);

  EXECUTE $replacement_head$#{definition}$replacement_head$ || chr(10) || settings_clauses
    || $replacement_body$
AS $active_read$
#{String.trim_trailing(body)}$replacement_body$;

  SELECT * INTO STRICT replaced FROM pg_proc WHERE oid = target;

  IF (to_jsonb(replaced) - 'prosrc') IS DISTINCT FROM (to_jsonb(prior) - 'prosrc')
    OR encode(sha256(convert_to(replaced.prosrc, 'UTF8')), 'hex') <> '#{to}'
  THEN
    RAISE EXCEPTION 'active-load replacement differs from the admitted definition';
  END IF;
END;
$active_read_upgrade$;

COMMIT;
""")
