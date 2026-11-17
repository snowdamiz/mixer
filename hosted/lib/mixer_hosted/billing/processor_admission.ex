defmodule MixerHosted.Billing.ProcessorAdmission do
  @moduledoc "Read-only startup gate. Billing role grants must be provisioned separately."
  use GenServer
  def start_link(:billing_v1), do: GenServer.start_link(__MODULE__, :billing_v1)
  @impl true
  def init(:billing_v1) do
    case MixerHosted.Repo.transaction(fn ->
           check!(fn sql -> MixerHosted.Repo.query!(sql).rows end)
         end) do
      {:ok, :ok} -> {:ok, :admitted}
      _ -> {:stop, :billing_processor_admission_refused}
    end
  end

  def after_connect(connection),
    do: check!(fn sql -> Postgrex.query!(connection, sql, []).rows end)

  @doc false
  def check!(q) when is_function(q, 1) do
    [[true]] =
      q.("""
      SELECT current_user='mixer_billing_processor' AND session_user=current_user
        AND NOT rolsuper AND NOT rolbypassrls AND NOT rolcreaterole AND NOT rolcreatedb
        AND NOT rolreplication AND NOT rolinherit
        AND NOT EXISTS(SELECT 1 FROM pg_auth_members WHERE member=pg_roles.oid)
        AND NOT has_database_privilege(current_user,current_database(),'CREATE')
        AND has_schema_privilege(current_user,'public','USAGE')
        AND NOT has_schema_privilege(current_user,'public','CREATE')
      FROM pg_roles WHERE rolname=current_user
      """)

    [[true]] =
      q.("""
      WITH required(name, privileges) AS (VALUES
        ('mixer_billing_reconciliations', ARRAY['SELECT','INSERT']::text[]),
        ('mixer_billing_subscription_claims', ARRAY['SELECT','INSERT']::text[]),
        ('mixer_billing_observations', ARRAY['SELECT','INSERT']::text[]),
        ('oban_jobs', ARRAY['SELECT','INSERT','UPDATE','DELETE']::text[]),
        ('oban_peers', ARRAY['SELECT','INSERT','UPDATE','DELETE']::text[]),
        ('mixer_billing_webhook_inbox', ARRAY['SELECT']::text[]),
        ('mixer_billing_credentials', ARRAY['SELECT']::text[]),
        ('mixer_billing_endpoints', ARRAY['SELECT']::text[]),
        ('mixer_billing_customer_bindings', ARRAY['SELECT']::text[]),
        ('mixer_billing_resource_links', ARRAY['SELECT']::text[]),
        ('mixer_billing_organization_state', ARRAY['SELECT']::text[])
      ), column_updates(name, col) AS (VALUES
        ('mixer_billing_reconciliations','state'),
        ('mixer_billing_reconciliations','reason'),
        ('mixer_billing_reconciliations','token'),
        ('mixer_billing_reconciliations','fence'),
        ('mixer_billing_subscription_claims','inbox_id'),
        ('mixer_billing_subscription_claims','token'),
        ('mixer_billing_subscription_claims','fence'),
        ('mixer_billing_subscription_claims','deadline'),
        ('mixer_billing_webhook_inbox','_billing_row_lock'),
        ('mixer_billing_credentials','_billing_row_lock'),
        ('mixer_billing_endpoints','_billing_row_lock'),
        ('mixer_billing_customer_bindings','_billing_row_lock'),
        ('mixer_billing_resource_links','_billing_row_lock'),
        ('mixer_billing_organization_state','_billing_row_lock')
      ), relations AS (
        SELECT c.*, n.nspname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname !~ '^pg_' AND n.nspname<>'information_schema'
          AND c.relkind IN ('r','p','v','m','f','S')
      ), table_ops(op) AS (
        SELECT unnest(ARRAY['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER'] ||
          CASE WHEN current_setting('server_version_num')::int>=170000
            THEN ARRAY['MAINTAIN']::text[] ELSE ARRAY[]::text[] END)
      )
      SELECT current_setting('server_version_num')::int BETWEEN 160000 AND 179999
        AND NOT EXISTS (
          SELECT 1 FROM required r
          LEFT JOIN relations c ON c.nspname='public' AND c.relname=r.name AND c.relkind IN ('r','p')
          WHERE c.oid IS NULL OR EXISTS (
            SELECT 1 FROM unnest(r.privileges) p(op)
            WHERE NOT has_table_privilege(current_user,c.oid,p.op)))
        AND NOT EXISTS (
          SELECT 1 FROM relations c WHERE pg_has_role(current_user,c.relowner,'USAGE'))
        AND NOT EXISTS (
          SELECT 1 FROM relations c CROSS JOIN table_ops p
          LEFT JOIN required r ON c.nspname='public' AND c.relname=r.name
          WHERE c.relkind<>'S' AND (
            has_table_privilege(current_user,c.oid,p.op || ' WITH GRANT OPTION')
            OR (has_table_privilege(current_user,c.oid,p.op)
              AND NOT COALESCE(p.op=ANY(r.privileges),false))))
        AND NOT EXISTS (
          SELECT 1 FROM relations c JOIN pg_attribute a ON a.attrelid=c.oid
          CROSS JOIN (VALUES ('SELECT'),('INSERT'),('UPDATE'),('REFERENCES')) p(op)
          LEFT JOIN required r ON c.nspname='public' AND c.relname=r.name
          WHERE c.relkind<>'S' AND a.attnum>0 AND NOT a.attisdropped AND (
            has_column_privilege(current_user,c.oid,a.attnum,p.op || ' WITH GRANT OPTION')
            OR (has_column_privilege(current_user,c.oid,a.attnum,p.op)
              AND NOT (COALESCE(p.op=ANY(r.privileges),false)
                OR (p.op='UPDATE' AND c.nspname='public' AND EXISTS (
                  SELECT 1 FROM column_updates u WHERE u.name=c.relname AND u.col=a.attname)))) ))
        AND NOT EXISTS (
          SELECT 1 FROM column_updates u
          LEFT JOIN relations c ON c.nspname='public' AND c.relname=u.name
          LEFT JOIN pg_attribute a ON a.attrelid=c.oid AND a.attname=u.col
            AND a.attnum>0 AND NOT a.attisdropped
          LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum
          WHERE a.attnum IS NULL OR NOT has_column_privilege(current_user,c.oid,a.attnum,'UPDATE')
            OR (u.col='_billing_row_lock' AND
              (a.attgenerated<>'s' OR a.atttypid<>'boolean'::regtype
                OR pg_get_expr(d.adbin,d.adrelid) IS DISTINCT FROM 'true')))
        AND to_regclass('public.oban_jobs_id_seq') IS NOT NULL
        AND has_sequence_privilege(current_user,'public.oban_jobs_id_seq','USAGE')
        AND NOT EXISTS (
          SELECT 1 FROM relations c CROSS JOIN (VALUES ('USAGE'),('SELECT'),('UPDATE')) p(op)
          WHERE c.relkind='S' AND (
            has_sequence_privilege(current_user,c.oid,p.op || ' WITH GRANT OPTION')
            OR (has_sequence_privilege(current_user,c.oid,p.op)
              AND NOT (c.nspname='public' AND c.relname='oban_jobs_id_seq' AND p.op='USAGE'))))
      """)

    :ok
  end
end
