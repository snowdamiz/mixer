BEGIN;
SET LOCAL search_path = pg_catalog;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

LOCK TABLE public.mixer_customer_idempotency IN ACCESS EXCLUSIVE MODE;

DO $restore$
DECLARE
  restored text;
  flattened CONSTANT text :=
    $expr$((octet_length(key) >= 1) AND (octet_length(key) <= 128) AND (key ~ '^[A-Za-z0-9_.:-]+$'::text))$expr$;
  pinned CONSTANT text :=
    $expr$(((octet_length(key) >= 1) AND (octet_length(key) <= 128)) AND (key ~ '^[A-Za-z0-9_.:-]+$'::text))$expr$;
BEGIN
  SELECT pg_get_expr(conbin, conrelid, false) INTO STRICT restored
  FROM pg_constraint
  WHERE conrelid = 'public.mixer_customer_idempotency'::regclass
    AND conname = 'mixer_customer_idempotency_key_check'
    AND contype = 'c' AND convalidated AND conislocal
    AND coninhcount = 0 AND NOT connoinherit AND conparentid = 0;

  IF restored = pinned THEN
    RETURN;
  END IF;
  IF restored IS DISTINCT FROM flattened THEN
    RAISE EXCEPTION 'Unexpected restored artifact request-key CHECK';
  END IF;

  ALTER TABLE public.mixer_customer_idempotency
    DROP CONSTRAINT mixer_customer_idempotency_key_check,
    ADD CONSTRAINT mixer_customer_idempotency_key_check
      CHECK (octet_length(key) BETWEEN 1 AND 128 AND key ~ '^[A-Za-z0-9_.:-]+$');

  IF (SELECT pg_get_expr(conbin, conrelid, false) FROM pg_constraint
      WHERE conrelid = 'public.mixer_customer_idempotency'::regclass
        AND conname = 'mixer_customer_idempotency_key_check' AND convalidated) IS DISTINCT FROM pinned THEN
    RAISE EXCEPTION 'Could not reproduce the pinned artifact request-key CHECK';
  END IF;
END
$restore$;

COMMIT;
