defmodule MixerHosted.Repo.Migrations.AddFencedBuildOperationIntent do
  use Ecto.Migration

  # Install as browser_schema_owner after 498 and 499. The operator separately
  # chooses whether to grant the builds_v1 role execution of this entry point.
  def up do
    body = File.read!(Path.join(__DIR__, "05_processor_intent_body.sql"))

    execute("""
    CREATE FUNCTION public.mixer_build_operation_intent_v1(
      p_action text, p_id text, p_ref bytea, p_spec bytea, p_deadline bigint,
      p_record uuid, p_epoch bigint, p_revision bigint, p_owner text, p_expires timestamptz,
      p_ref_scope jsonb, p_spec_scope jsonb
    ) RETURNS TABLE(outcome text, admission_state text, lease_epoch bigint, journal_revision bigint)
    LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public, pg_temp
    AS $intent$#{body}$intent$
    """)

    execute("""
    REVOKE ALL ON FUNCTION public.mixer_build_operation_intent_v1(
      text,text,bytea,bytea,bigint,uuid,bigint,bigint,text,timestamptz,jsonb,jsonb
    ) FROM PUBLIC
    """)
  end

  def down do
    raise "disable durable intent before an explicit operation admission migration"
  end
end
