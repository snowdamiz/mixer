BEGIN;

CREATE ROLE mixer_release_delivery LOGIN NOINHERIT NOSUPERUSER
  NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT CONNECT ON DATABASE :"DBNAME" TO mixer_release_delivery;
GRANT USAGE ON SCHEMA public TO mixer_release_delivery;
GRANT EXECUTE ON FUNCTION
  public.mixer_release_delivery_offer(text,text,text,text,text,text,text),
  public.mixer_release_delivery_artifact(text,text,text,text,text,text,text,text)
TO mixer_release_delivery;

COMMIT;
