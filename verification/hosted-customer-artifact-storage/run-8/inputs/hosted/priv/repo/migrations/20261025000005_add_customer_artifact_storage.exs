defmodule MixerHosted.Repo.Migrations.AddCustomerArtifactStorage do
  use Ecto.Migration
  alias MixerHosted.CustomerArtifacts.Schema

  def up, do: Enum.each(Schema.statements(), &execute/1)

  def down do
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
