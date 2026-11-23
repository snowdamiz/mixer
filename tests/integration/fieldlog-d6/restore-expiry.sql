\set ON_ERROR_STOP on

BEGIN;
SET LOCAL search_path = pg_catalog;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

LOCK TABLE public.mixer_authz_credentials, public.mixer_authz_families IN ACCESS EXCLUSIVE MODE;

DO $restore$
DECLARE
  table_name text;
  constraint_name text;
  actual text;
  flattened CONSTANT text :=
    $expr$((expires_at >= 0) AND (expires_at <= '9007199254740991'::bigint) AND (expires_at > not_before))$expr$;
  pinned CONSTANT text :=
    $expr$(((expires_at >= 0) AND (expires_at <= '9007199254740991'::bigint)) AND (expires_at > not_before))$expr$;
BEGIN
  IF current_setting('server_version_num')::integer / 10000 <> 17 THEN
    RAISE EXCEPTION 'This restore procedure is verified for PostgreSQL 17';
  END IF;

  FOREACH table_name IN ARRAY ARRAY['mixer_authz_credentials', 'mixer_authz_families'] LOOP
    constraint_name := table_name || '_check';

    SELECT pg_get_expr(c.conbin, c.conrelid, false) INTO STRICT actual
      FROM pg_constraint AS c
     WHERE c.conrelid = format('public.%I', table_name)::regclass
       AND c.conname = constraint_name
       AND c.contype = 'c' AND c.convalidated AND c.conislocal
       AND c.coninhcount = 0 AND NOT c.connoinherit AND c.conparentid = 0;

    IF actual = pinned THEN
      CONTINUE;
    END IF;
    IF actual IS DISTINCT FROM flattened THEN
      RAISE EXCEPTION 'Unexpected restored CHECK on public.%', table_name;
    END IF;

    EXECUTE format(
      'ALTER TABLE public.%I DROP CONSTRAINT %I, ADD CONSTRAINT %I
         CHECK (expires_at BETWEEN 0 AND 9007199254740991 AND expires_at > not_before)',
      table_name, constraint_name, constraint_name
    );

    IF (SELECT pg_get_expr(conbin, conrelid, false)
          FROM pg_constraint
         WHERE conrelid = format('public.%I', table_name)::regclass
           AND conname = constraint_name AND convalidated) IS DISTINCT FROM pinned THEN
      RAISE EXCEPTION 'Could not reproduce the pinned CHECK on public.%', table_name;
    END IF;
  END LOOP;
END
$restore$;

COMMIT;
