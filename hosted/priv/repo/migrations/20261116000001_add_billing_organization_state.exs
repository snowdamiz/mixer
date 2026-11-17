defmodule MixerHosted.Repo.Migrations.AddBillingOrganizationState do
  use Ecto.Migration

  def up do
    execute("""
    CREATE TABLE public.mixer_billing_organization_state (
      organization_id text PRIMARY KEY REFERENCES public.mixer_authz_organizations(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
      active boolean NOT NULL,
      revision bigint NOT NULL DEFAULT 1 CHECK(revision>0),
      _billing_row_lock boolean GENERATED ALWAYS AS (true) STORED
    );
    """)

    execute("""
    INSERT INTO public.mixer_billing_organization_state(organization_id,active)
      SELECT id,active FROM public.mixer_authz_organizations;
    """)

    execute("""
    CREATE FUNCTION public.mixer_billing_organization_sync() RETURNS trigger
      LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $$
    BEGIN
      IF TG_OP='DELETE' THEN
        DELETE FROM public.mixer_billing_organization_state WHERE organization_id=OLD.id;
        RETURN OLD;
      END IF;
      INSERT INTO public.mixer_billing_organization_state(organization_id,active)
        VALUES(NEW.id,NEW.active)
        ON CONFLICT(organization_id) DO UPDATE SET active=EXCLUDED.active,
          revision=public.mixer_billing_organization_state.revision+1;
      RETURN NEW;
    END $$;
    """)

    execute("""
    CREATE TRIGGER billing_organization_sync AFTER INSERT OR UPDATE OR DELETE
      ON public.mixer_authz_organizations FOR EACH ROW
      EXECUTE FUNCTION public.mixer_billing_organization_sync();
    """)
  end

  def down do
    execute("DROP TRIGGER billing_organization_sync ON public.mixer_authz_organizations")
    execute("DROP FUNCTION public.mixer_billing_organization_sync()")
    execute("DROP TABLE public.mixer_billing_organization_state")
  end
end
