defmodule MixerHosted.Repo.Migrations.AddLocalReleaseDeliveryPublishFence do
  use Ecto.Migration

  @reader "mixer_release_delivery"
  @heads "public.mixer_release_heads"
  @enrollments "public.mixer_release_delivery_enrollments"
  @export "public.mixer_release_delivery_export"
  @fence "public.mixer_release_delivery_lock_current"
  @arguments "(text,text,text,text,text,text,text)"
  @key ~w(organization_id project_id application_id environment_id platform runtime_sha256 channel)
  @params "org,proj,app,env,os,runtime,lane"

  def up do
    execute("""
    DO $body$
    BEGIN
      IF (SELECT count(*) FROM pg_catalog.pg_class c
          JOIN pg_catalog.pg_roles r ON r.oid=c.relowner
          WHERE c.oid IN ('#{@heads}'::regclass,'#{@enrollments}'::regclass)
            AND c.relrowsecurity AND c.relforcerowsecurity AND r.rolname=current_user
            AND NOT r.rolcanlogin AND NOT r.rolsuper AND NOT r.rolbypassrls) <> 2
        OR NOT EXISTS (SELECT 1 FROM pg_catalog.pg_proc p
                       WHERE p.oid = '#{@export}#{@arguments}'::regprocedure
                         AND pg_catalog.pg_get_userbyid(p.proowner)=current_user AND p.prosecdef)
      THEN
        RAISE EXCEPTION 'delivery publish fence requires the restricted ledger and export owner';
      END IF;
    END
    $body$
    """)

    # FOR SHARE requires UPDATE visibility. Only the definer can use this
    # policy, and its WITH CHECK cannot authorize an actual head update.
    execute("""
    CREATE POLICY release_delivery_lock_head ON #{@heads} FOR UPDATE TO CURRENT_USER
    USING (session_user = '#{@reader}' AND current_user <> session_user)
    WITH CHECK (false)
    """)

    execute("""
    CREATE FUNCTION #{@fence}(org text, proj text, app text, env text, os text, runtime text, lane text)
    RETURNS boolean
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog
    AS $body$
    BEGIN
      IF session_user <> '#{@reader}' OR current_user = session_user OR
         EXISTS (SELECT 1 FROM pg_catalog.pg_roles r
                 WHERE pg_catalog.pg_has_role(session_user,r.oid,'MEMBER') AND
                   (r.rolname=current_user OR r.rolsuper OR r.rolbypassrls OR r.rolcreaterole OR
                    r.rolcreatedb OR r.rolreplication OR left(r.rolname::text,3)='pg_')) THEN
        RETURN false;
      END IF;

      PERFORM 1 FROM #{@enrollments} e
      WHERE e.reader_role = session_user AND (#{columns("e")}) = (#{@params})
      FOR SHARE OF e NOWAIT;
      IF NOT FOUND THEN
        RETURN false;
      END IF;

      PERFORM 1 FROM #{@heads} h
      WHERE (#{columns("h")}) = (#{@params}) AND h.sequence IS NOT NULL
      FOR SHARE OF h NOWAIT;
      RETURN FOUND;
    END
    $body$
    """)

    execute("REVOKE ALL ON FUNCTION #{@fence}#{@arguments} FROM PUBLIC")
  end

  def down do
    execute("DROP FUNCTION #{@fence}#{@arguments}")
    execute("DROP POLICY release_delivery_lock_head ON #{@heads}")
  end

  defp columns(name), do: Enum.map_join(@key, ",", &"#{name}.#{&1}")
end
