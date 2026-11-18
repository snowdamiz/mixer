defmodule MixerHosted.Repo.Migrations.RestrictLegacyBillingTriggerExecute do
  use Ecto.Migration

  @functions ~w(mixer_billing_observation_immutable mixer_billing_organization_sync mixer_billing_scope_immutable mixer_usage_immutable)

  def up do
    signatures = Enum.map_join(@functions, ", ", &"public.#{&1}()")
    procedures = Enum.map_join(@functions, ", ", &"'public.#{&1}()'::pg_catalog.regprocedure")

    execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1
        FROM pg_catalog.pg_roles
        WHERE rolname = current_user
          AND NOT (rolcanlogin OR rolsuper OR rolbypassrls)
      ) OR EXISTS (
        SELECT 1
        FROM pg_catalog.pg_proc p
        JOIN pg_catalog.pg_roles owner ON owner.oid = p.proowner
        WHERE p.oid IN (#{procedures})
          AND (owner.rolname <> current_user OR p.prorettype <> 'pg_catalog.trigger'::pg_catalog.regtype)
      ) THEN
        RAISE insufficient_privilege USING
          MESSAGE = 'billing trigger ACL migration requires the restricted owner of all four trigger functions';
      END IF;
    END $$;
    """)

    execute("REVOKE EXECUTE ON FUNCTION #{signatures} FROM PUBLIC")

    # The previous migration's rollback needs to recreate the legacy trigger.
    execute("""
    DO $$
    BEGIN
      IF NOT pg_catalog.has_function_privilege(
        current_user, 'public.mixer_billing_organization_sync()', 'EXECUTE'
      ) THEN
        GRANT EXECUTE ON FUNCTION public.mixer_billing_organization_sync() TO CURRENT_USER;
      END IF;
    END $$;
    """)
  end

  def down do
    # A database may already have removed PUBLIC EXECUTE. Rollback preserves that restriction.
    :ok
  end
end
