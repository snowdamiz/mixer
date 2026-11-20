BEGIN;

CREATE ROLE mixer_artifact_uploader LOGIN NOINHERIT NOSUPERUSER
  NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT CONNECT ON DATABASE :"DBNAME" TO mixer_artifact_uploader;
GRANT USAGE ON SCHEMA public TO mixer_artifact_uploader;

GRANT SELECT ON
  public.mixer_authz_profiles, public.mixer_authz_principals,
  public.mixer_authz_bindings, public.mixer_authz_families,
  public.mixer_authz_credentials, public.mixer_authz_organizations,
  public.mixer_authz_projects, public.mixer_authz_applications,
  public.mixer_authz_environments, public.mixer_authz_organization_heads,
  public.mixer_authz_project_heads, public.mixer_authz_memberships
TO mixer_artifact_uploader;

GRANT EXECUTE ON FUNCTION
  public.mixer_authz_lock_profiles(), public.mixer_authz_lock_principals(),
  public.mixer_authz_lock_families(), public.mixer_authz_lock_credentials(),
  public.mixer_authz_lock_organization_heads(), public.mixer_authz_lock_project_heads(),
  public.mixer_customer_allowed(text,text,text,text,text,boolean),
  public.mixer_customer_artifact_metadata(text),
  public.mixer_customer_key_exists(text)
TO mixer_artifact_uploader;

GRANT SELECT, INSERT ON
  public.mixer_customer_artifacts, public.mixer_customer_audit_events,
  public.mixer_customer_idempotency
TO mixer_artifact_uploader;

GRANT SELECT, UPDATE (sequence, event_sha256, state_sha256)
ON public.mixer_customer_artifact_heads TO mixer_artifact_uploader;

COMMIT;
