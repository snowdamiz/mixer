defmodule MixerHosted.Repo.Migrations.AllowFreeWorkspaceBillingStateSync do
  use Ecto.Migration

  def up do
    require_relation_owner()

    # Synchronize the row already written under workspace authorization.
    # Workspace roles receive no billing table privileges.
    execute("""
    CREATE FUNCTION public.mixer_free_workspace_sync_billing_state_v1() RETURNS trigger
      LANGUAGE plpgsql SECURITY DEFINER SET search_path TO pg_catalog AS $$
    BEGIN
      IF TG_RELID <> 'public.mixer_authz_organizations'::regclass
         OR TG_LEVEL <> 'ROW' OR TG_WHEN <> 'AFTER' THEN
        RAISE insufficient_privilege USING MESSAGE = 'invalid organization state trigger';
      END IF;

      IF TG_OP = 'DELETE' THEN
        DELETE FROM public.mixer_billing_organization_state WHERE organization_id = OLD.id;
        RETURN OLD;
      END IF;

      INSERT INTO public.mixer_billing_organization_state (organization_id, active)
        VALUES (NEW.id, NEW.active)
        ON CONFLICT (organization_id) DO UPDATE
          SET active = EXCLUDED.active,
              revision = public.mixer_billing_organization_state.revision + 1;

      RETURN NEW;
    END $$;
    """)

    # Defaults can grant EXECUTE to named roles or remove it from the owner.
    execute(
      "REVOKE ALL ON FUNCTION public.mixer_free_workspace_sync_billing_state_v1() FROM PUBLIC"
    )

    execute("""
    DO $$
    DECLARE
      grantee name;
    BEGIN
      FOR grantee IN
        SELECT DISTINCT r.rolname
        FROM pg_catalog.pg_proc p
        CROSS JOIN LATERAL pg_catalog.aclexplode(p.proacl) acl
        JOIN pg_catalog.pg_roles r ON r.oid = acl.grantee
        WHERE p.oid = 'public.mixer_free_workspace_sync_billing_state_v1()'::pg_catalog.regprocedure
          AND acl.grantee <> p.proowner
      LOOP
        EXECUTE pg_catalog.format(
          'REVOKE ALL ON FUNCTION public.mixer_free_workspace_sync_billing_state_v1() FROM %I',
          grantee
        );
      END LOOP;
    END $$;
    """)

    execute(
      "GRANT EXECUTE ON FUNCTION public.mixer_free_workspace_sync_billing_state_v1() TO CURRENT_USER"
    )

    replace_trigger("mixer_free_workspace_sync_billing_state_v1")
  end

  def down do
    require_relation_owner()
    replace_trigger("mixer_billing_organization_sync")
    execute("DROP FUNCTION public.mixer_free_workspace_sync_billing_state_v1()")
  end

  defp require_relation_owner do
    execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_roles r
        WHERE r.rolname = current_user
          AND NOT (r.rolcanlogin OR r.rolsuper OR r.rolbypassrls)
          AND r.oid = (
            SELECT relowner FROM pg_catalog.pg_class
            WHERE oid = 'public.mixer_authz_organizations'::pg_catalog.regclass
          )
          AND r.oid = (
            SELECT relowner FROM pg_catalog.pg_class
            WHERE oid = 'public.mixer_billing_organization_state'::pg_catalog.regclass
          )
      ) THEN
        RAISE insufficient_privilege USING
          MESSAGE = 'billing state sync migration requires the restricted owner of both relations';
      END IF;
    END $$;
    """)
  end

  defp replace_trigger(function) do
    execute("DROP TRIGGER billing_organization_sync ON public.mixer_authz_organizations")

    execute("""
    CREATE TRIGGER billing_organization_sync AFTER INSERT OR UPDATE OR DELETE
      ON public.mixer_authz_organizations FOR EACH ROW
      EXECUTE FUNCTION public.#{function}();
    """)
  end
end
