defmodule MixerHosted.Repo.Migrations.AddCustomerArtifactStorage do
  use Ecto.Migration
  alias MixerHosted.CustomerArtifacts.Schema

  def up, do: Enum.each(Schema.statements(), &execute/1)

  def down do
    # Owner-only policies reference the artifact relation to compare owners.
    # Remove only this migration's exact policies before dropping those tables;
    # a broad CASCADE could silently remove unrelated dependent objects.
    for {table, policies} <- [
          {"artifact_heads", ~w(customer_read customer_transition customer_integrity_owner)},
          {"artifacts",
           ~w(customer_read customer_insert customer_metadata_owner customer_integrity_owner)},
          {"audit_events", ~w(customer_read customer_insert customer_integrity_owner)},
          {"idempotency", ~w(customer_read customer_insert customer_integrity_owner)}
        ],
        policy <- policies do
      execute("DROP POLICY #{policy} ON public.mixer_customer_#{table}")
    end

    for table <- ~w(artifact_heads artifacts audit_events idempotency) do
      execute("DROP TRIGGER customer_integrity ON public.mixer_customer_#{table}")
    end

    for table <- ~w(artifacts audit_events idempotency) do
      execute("DROP TRIGGER customer_immutable ON public.mixer_customer_#{table}")
    end

    execute(
      "ALTER TABLE public.mixer_customer_artifacts DROP CONSTRAINT mixer_customer_artifacts_creating_event"
    )

    for table <- ~w(idempotency audit_events artifacts artifact_heads),
        do: execute("DROP TABLE public.mixer_customer_#{table}")

    for name <-
          ~w(mixer_customer_integrity mixer_customer_immutable mixer_customer_event_identity mixer_customer_json_shape mixer_customer_key_exists mixer_customer_artifact_metadata mixer_customer_allowed mixer_customer_hash mixer_customer_cbor mixer_customer_cbor_part mixer_customer_cbor_head) do
      execute("DROP FUNCTION public.#{name}(#{Schema.signatures()[name]})")
    end
  end
end
