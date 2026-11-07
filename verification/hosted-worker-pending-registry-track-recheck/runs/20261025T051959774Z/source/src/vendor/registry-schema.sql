CREATE TABLE IF NOT EXISTS pending_registry_meta(singleton INTEGER PRIMARY KEY CHECK(singleton=1),version INTEGER NOT NULL CHECK(version=1),config TEXT NOT NULL,shard INTEGER NOT NULL CHECK(shard BETWEEN 0 AND 15),allocated INTEGER NOT NULL CHECK(allocated BETWEEN 0 AND 4096));
CREATE TABLE IF NOT EXISTS pending_registry_record(
 allocation_index INTEGER PRIMARY KEY CHECK(allocation_index BETWEEN 1 AND 4096),
 operation_key TEXT NOT NULL UNIQUE,identity_bytes TEXT NOT NULL,identity_digest TEXT NOT NULL UNIQUE,record_id TEXT NOT NULL UNIQUE,
 state_version TEXT NOT NULL,projection_json TEXT NOT NULL,pending INTEGER NOT NULL CHECK(pending IN(0,1)),
 failures INTEGER NOT NULL CHECK(failures BETWEEN 0 AND 32),skip_visits INTEGER NOT NULL CHECK(skip_visits BETWEEN 0 AND 7),needs_attention INTEGER NOT NULL CHECK(needs_attention IN(0,1)),
 attempt_sequence TEXT NOT NULL,last_run_id TEXT,last_visit TEXT CHECK(last_visit IS NULL OR last_visit IN('reserved','backoff')),
 ticket_json TEXT,disposition_json TEXT
);
CREATE INDEX IF NOT EXISTS pending_registry_due ON pending_registry_record(pending,allocation_index);
