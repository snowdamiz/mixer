CREATE TABLE IF NOT EXISTS controller_schema(version INTEGER NOT NULL CHECK(version=3));
INSERT INTO controller_schema(version) SELECT 3 WHERE NOT EXISTS(SELECT 1 FROM controller_schema);
CREATE TABLE IF NOT EXISTS operation (
 singleton INTEGER PRIMARY KEY CHECK(singleton=1),
 operation_id TEXT NOT NULL, binding TEXT NOT NULL, binding_hash TEXT NOT NULL,
 request_json TEXT NOT NULL, epoch TEXT NOT NULL, revision TEXT NOT NULL,
 owner TEXT NOT NULL, expiry_us TEXT NOT NULL,
 clock_lower TEXT NOT NULL, clock_upper TEXT NOT NULL, clock_qualification TEXT NOT NULL, clock_floor TEXT NOT NULL,
 desired TEXT NOT NULL CHECK(desired IN ('none','run','stop')),
 phase TEXT NOT NULL CHECK(phase IN ('unlaunched','launch_pending','inert','claim_consumed','running','stop_pending','completed','stopped','uncertain','quarantined')),
 provider_key TEXT NOT NULL, provider_kind TEXT NOT NULL,
 state_version TEXT NOT NULL, claim_state TEXT NOT NULL CHECK(claim_state IN ('unissued','consumed','revoked')),
 claim_id TEXT, instance_id TEXT, boot_id TEXT,
 effect_id TEXT, effect_request_json TEXT, effect_kind TEXT CHECK(effect_kind IS NULL OR effect_kind IN ('launch','inspect','stop')),
 effect_state TEXT NOT NULL CHECK(effect_state IN ('none','prepared','dispatched','uncertain','settled')),
 launch_dispatched INTEGER NOT NULL CHECK(launch_dispatched IN (0,1)),
 terminal_json TEXT, report_hash TEXT, pending_result_json TEXT,
 next_due_us TEXT, failures INTEGER NOT NULL CHECK(failures BETWEEN 0 AND 32),
 quarantined INTEGER NOT NULL CHECK(quarantined IN (0,1)),
 pending_identity_json TEXT, registration_json TEXT,
 registry_ack_version TEXT NOT NULL DEFAULT '0',
 effect_barrier_version TEXT, claim_barrier_version TEXT,
 track_outbox_json TEXT
);
CREATE TABLE IF NOT EXISTS audit (
 sequence INTEGER PRIMARY KEY CHECK(sequence BETWEEN 0 AND 31),
 kind TEXT NOT NULL CHECK(length(kind)<=64),
 state_version TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS registry_quarantine (
 singleton INTEGER PRIMARY KEY CHECK(singleton=1),
 identity_bytes TEXT NOT NULL CHECK(length(identity_bytes)<=2048),
 observed_version TEXT NOT NULL, reason TEXT NOT NULL CHECK(length(reason)<=64)
);
