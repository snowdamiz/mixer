-- UNSELECTED candidate. Trusted internal storage, not worker authentication.
CREATE TABLE mixer_build_operation_admissions (
  operation_id text PRIMARY KEY CHECK (operation_id ~ '^[0-9a-f]{64}$'),
  original_ref bytea NOT NULL,
  original_spec bytea NOT NULL,
  deadline_ms bigint NOT NULL CHECK (deadline_ms >= 0),
  record_id uuid NOT NULL,
  lease_epoch bigint NOT NULL CHECK (lease_epoch > 0),
  journal_revision bigint NOT NULL CHECK (journal_revision BETWEEN 0 AND 32),
  owner_id text NOT NULL CHECK (length(owner_id) BETWEEN 1 AND 128),
  admission_state text NOT NULL CHECK (admission_state IN ('unadmitted', 'admitted', 'stop_intent')),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

