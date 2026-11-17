defmodule MixerHosted.Repo.Migrations.AddBillingReconciliation do
  use Ecto.Migration

  def up do
    execute("""
    CREATE TABLE mixer_billing_credentials (
      id uuid PRIMARY KEY, account text NOT NULL CHECK(account ~ '^acct_[A-Za-z0-9]{1,123}$'),
      livemode boolean NOT NULL, secret_ref text NOT NULL CHECK(octet_length(secret_ref) BETWEEN 1 AND 128),
      attestation text NOT NULL CHECK(octet_length(attestation) BETWEEN 1 AND 256),
      active boolean NOT NULL, revision bigint NOT NULL DEFAULT 1 CHECK(revision>0)
    );
    """)

    execute("""
    CREATE TABLE mixer_billing_endpoints (
      id text PRIMARY KEY CHECK(octet_length(id) BETWEEN 1 AND 255), event_account text,
      livemode boolean NOT NULL, credential_id uuid NOT NULL REFERENCES mixer_billing_credentials(id),
      active boolean NOT NULL, revision bigint NOT NULL DEFAULT 1 CHECK(revision>0)
    );
    """)

    execute("""
    CREATE TABLE mixer_billing_customer_bindings (
      id uuid PRIMARY KEY, organization_id text NOT NULL REFERENCES mixer_authz_organizations(id),
      endpoint_id text NOT NULL REFERENCES mixer_billing_endpoints(id),
      customer_id text NOT NULL CHECK(customer_id ~ '^cus_[A-Za-z0-9]{1,124}$'),
      provisioning_evidence text NOT NULL CHECK(octet_length(provisioning_evidence) BETWEEN 1 AND 256),
      active boolean NOT NULL, revision bigint NOT NULL DEFAULT 1 CHECK(revision>0),
      UNIQUE(endpoint_id,customer_id)
    );
    """)

    execute("""
    CREATE TABLE mixer_billing_resource_links (
      binding_id uuid NOT NULL REFERENCES mixer_billing_customer_bindings(id),
      kind text NOT NULL CHECK(kind IN ('subscription','invoice','checkout.session')),
      object_id text NOT NULL CHECK(octet_length(object_id) BETWEEN 1 AND 128),
      subscription_id text NOT NULL CHECK(subscription_id ~ '^sub_[A-Za-z0-9]{1,124}$'),
      provisioning_evidence text NOT NULL CHECK(octet_length(provisioning_evidence) BETWEEN 1 AND 256),
      active boolean NOT NULL, revision bigint NOT NULL DEFAULT 1 CHECK(revision>0),
      PRIMARY KEY(binding_id,kind,object_id)
    );
    """)

    execute("""
    CREATE TABLE mixer_billing_reconciliations (
      inbox_id uuid PRIMARY KEY REFERENCES mixer_billing_webhook_inbox(id),
      state text NOT NULL CHECK(state IN ('pending','claimed','retry','blocked','refused')),
      reason text CHECK(reason IN ('relationship_unavailable','ordering_unavailable','provider_unavailable')),
      token uuid, fence bigint NOT NULL DEFAULT 0 CHECK(fence>=0)
    );
    """)

    execute("""
    CREATE TABLE mixer_billing_subscription_claims (
      binding_id uuid NOT NULL REFERENCES mixer_billing_customer_bindings(id),
      subscription_id text NOT NULL CHECK(subscription_id ~ '^sub_[A-Za-z0-9]{1,124}$'),
      inbox_id uuid REFERENCES mixer_billing_webhook_inbox(id), token uuid,
      fence bigint NOT NULL DEFAULT 0 CHECK(fence>=0), deadline timestamptz,
      PRIMARY KEY(binding_id,subscription_id), CHECK((token IS NULL)=(deadline IS NULL))
    );
    """)

    execute("""
    CREATE TABLE mixer_billing_observations (
      inbox_id uuid PRIMARY KEY REFERENCES mixer_billing_reconciliations(inbox_id),
      binding_id uuid NOT NULL REFERENCES mixer_billing_customer_bindings(id),
      subscription_id text NOT NULL, fence bigint NOT NULL CHECK(fence>0),
      organization_id text NOT NULL REFERENCES mixer_authz_organizations(id),
      account text NOT NULL, livemode boolean NOT NULL, customer_id text NOT NULL,
      status text NOT NULL CHECK(status IN ('incomplete','incomplete_expired','trialing','active','past_due','canceled','unpaid','paused')),
      response_sha256 bytea NOT NULL CHECK(octet_length(response_sha256)=32),
      provenance jsonb NOT NULL CHECK(octet_length(provenance::text)<=4096),
      observed_at timestamptz NOT NULL DEFAULT clock_timestamp()
    );
    """)

    execute("""
    CREATE FUNCTION mixer_billing_scope_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF (to_jsonb(NEW)-ARRAY['active','revision']) IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['active','revision'])
      THEN RAISE EXCEPTION 'billing scope is immutable'; END IF;
      NEW.revision := OLD.revision+1; RETURN NEW;
    END $$;
    """)

    execute("""
    CREATE TRIGGER billing_scope_immutable BEFORE UPDATE ON mixer_billing_credentials
      FOR EACH ROW EXECUTE FUNCTION mixer_billing_scope_immutable();
    """)

    execute("""
    CREATE TRIGGER billing_scope_immutable BEFORE UPDATE ON mixer_billing_endpoints
      FOR EACH ROW EXECUTE FUNCTION mixer_billing_scope_immutable();
    """)

    execute("""
    CREATE TRIGGER billing_scope_immutable BEFORE UPDATE ON mixer_billing_customer_bindings
      FOR EACH ROW EXECUTE FUNCTION mixer_billing_scope_immutable();
    """)

    execute("""
    CREATE TRIGGER billing_scope_immutable BEFORE UPDATE ON mixer_billing_resource_links
      FOR EACH ROW EXECUTE FUNCTION mixer_billing_scope_immutable();
    """)

    execute("""
    CREATE FUNCTION mixer_billing_observation_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'billing observation is immutable'; END $$;
    """)

    execute("""
    CREATE TRIGGER billing_observation_immutable BEFORE UPDATE OR DELETE ON mixer_billing_observations
      FOR EACH ROW EXECUTE FUNCTION mixer_billing_observation_immutable();
    """)

    execute("""
    ALTER TABLE mixer_billing_webhook_inbox ADD COLUMN _billing_row_lock boolean GENERATED ALWAYS AS (true) STORED;
    """)

    execute("""
    ALTER TABLE mixer_billing_credentials ADD COLUMN _billing_row_lock boolean GENERATED ALWAYS AS (true) STORED;
    """)

    execute("""
    ALTER TABLE mixer_billing_endpoints ADD COLUMN _billing_row_lock boolean GENERATED ALWAYS AS (true) STORED;
    """)

    execute("""
    ALTER TABLE mixer_billing_customer_bindings ADD COLUMN _billing_row_lock boolean GENERATED ALWAYS AS (true) STORED;
    """)

    execute("""
    ALTER TABLE mixer_billing_resource_links ADD COLUMN _billing_row_lock boolean GENERATED ALWAYS AS (true) STORED;
    """)

    execute("""
    ALTER TABLE mixer_authz_organizations ADD COLUMN _billing_row_lock boolean GENERATED ALWAYS AS (true) STORED;
    """)

    execute("""
    CREATE OR REPLACE FUNCTION mixer_billing_scope_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF (to_jsonb(NEW)-ARRAY['active','revision','_billing_row_lock']) IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['active','revision','_billing_row_lock'])
      THEN RAISE EXCEPTION 'billing scope is immutable'; END IF;
      NEW.revision := OLD.revision+1; RETURN NEW;
    END $$;
    """)
  end

  def down do
    execute("ALTER TABLE mixer_billing_webhook_inbox DROP COLUMN _billing_row_lock")
    execute("ALTER TABLE mixer_authz_organizations DROP COLUMN _billing_row_lock")

    for t <-
          ~w(observations subscription_claims reconciliations resource_links customer_bindings endpoints credentials),
        do: execute("DROP TABLE mixer_billing_#{t}")

    execute("DROP FUNCTION mixer_billing_scope_immutable()")
    execute("DROP FUNCTION mixer_billing_observation_immutable()")
  end
end
