defmodule MixerHosted.Repo.Migrations.AddBillingUsageLedger do
  use Ecto.Migration

  def up do
    create table(:mixer_billing_usage_entries, primary_key: false) do
      add(:id, :uuid, primary_key: true)
      add(:tenant_id, :text, null: false)
      add(:metric, :text, null: false)
      add(:platform, :text, null: false)
      add(:period_start, :bigint, null: false)
      add(:period_end, :bigint, null: false)
      add(:source, :text, null: false)
      add(:source_key, :text, null: false)
      add(:units, :bigint, null: false)
      add(:correction_of, :uuid)
      timestamps(type: :utc_datetime_usec, updated_at: false)
    end

    create(
      unique_index(:mixer_billing_usage_entries, [:tenant_id, :source, :source_key],
        name: :mixer_usage_identity
      )
    )

    create(
      unique_index(:mixer_billing_usage_entries, [:correction_of], name: :mixer_usage_successor)
    )

    create(
      index(
        :mixer_billing_usage_entries,
        [:tenant_id, :metric, :platform, :period_start, :period_end],
        name: :mixer_usage_scope
      )
    )

    execute("""
    ALTER TABLE mixer_billing_usage_entries
      ADD CONSTRAINT mixer_usage_parent_scope_key
        UNIQUE (id, tenant_id, metric, platform, period_start, period_end, source),
      ADD CONSTRAINT mixer_usage_parent_scope
        FOREIGN KEY (correction_of, tenant_id, metric, platform, period_start, period_end, source)
        REFERENCES mixer_billing_usage_entries
          (id, tenant_id, metric, platform, period_start, period_end, source),
      ADD CONSTRAINT mixer_usage_integer_units CHECK (units >= 0),
      ADD CONSTRAINT mixer_usage_period CHECK
        (period_start >= 0 AND period_end > period_start AND period_end <= 253402300799),
      ADD CONSTRAINT mixer_usage_identity_bounds CHECK
        (octet_length(tenant_id) BETWEEN 1 AND 128 AND
         octet_length(source) BETWEEN 1 AND 128 AND octet_length(source_key) BETWEEN 1 AND 128),
      ADD CONSTRAINT mixer_usage_metric CHECK (
        (metric = 'build_elapsed_milliseconds' AND platform IN ('ios', 'android')) OR
        (metric = 'storage_byte_seconds' AND platform = 'all') OR
        (metric = 'active_update_installations' AND platform = 'all' AND units IN (0, 1)
         AND (correction_of IS NOT NULL OR units = 1)
         AND (to_timestamp(period_start) AT TIME ZONE 'UTC') =
           date_trunc('month', to_timestamp(period_start) AT TIME ZONE 'UTC')
         AND (to_timestamp(period_end) AT TIME ZONE 'UTC') =
           (to_timestamp(period_start) AT TIME ZONE 'UTC') + INTERVAL '1 month')),
      ADD CONSTRAINT mixer_usage_no_self_correction CHECK (id IS DISTINCT FROM correction_of)
    """)

    execute("""
    CREATE FUNCTION mixer_usage_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP = 'INSERT' THEN
        IF NEW.correction_of IS NOT NULL AND NOT EXISTS
          (SELECT 1 FROM mixer_billing_usage_entries WHERE id = NEW.correction_of) THEN
          RAISE EXCEPTION 'usage predecessor must already exist' USING ERRCODE = '23503';
        END IF;
        RETURN NEW;
      END IF;
      RAISE EXCEPTION 'usage ledger is append-only' USING ERRCODE = '23514';
    END;
    $$
    """)

    execute("""
    CREATE TRIGGER mixer_usage_immutable BEFORE UPDATE OR DELETE OR TRUNCATE
      ON mixer_billing_usage_entries FOR EACH STATEMENT EXECUTE FUNCTION mixer_usage_immutable()
    """)

    execute("""
    CREATE TRIGGER mixer_usage_causal_append BEFORE INSERT ON mixer_billing_usage_entries
      FOR EACH ROW EXECUTE FUNCTION mixer_usage_immutable()
    """)
  end

  def down do
    drop(table(:mixer_billing_usage_entries))
    execute("DROP FUNCTION mixer_usage_immutable()")
  end
end
