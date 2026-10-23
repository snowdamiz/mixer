package release

import (
	"context"
	"embed"
	"encoding/json"
	"errors"
	"fmt"
	"net"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"mixer/services/internal/durable"
	"mixer/services/protocol"
)

//go:embed migrations/*.sql
var migrations embed.FS

// PostgreSQL remains an explicitly selected local development backend. A DSN is
// read from an operator-selected environment variable, never returned in errors.
type PostgresConfig struct {
	ConnectionStringEnv      string `json:"connection_string_env"`
	MaxConnections           int32  `json:"max_connections,omitempty"`
	QueryTimeoutMilliseconds uint64 `json:"query_timeout_milliseconds,omitempty"`
}
type postgresStore struct {
	pool    *pgxpool.Pool
	timeout time.Duration
	fault   durable.Fault
}

func storageError() error {
	return apiError{503, "storage_unavailable", "database operation unavailable; retry the same idempotency key"}
}
func rollbackPostgres(tx pgx.Tx) {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	_ = tx.Rollback(ctx)
}
func closePostgres(conn *pgx.Conn) {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	_ = conn.Close(ctx)
}
func postgresSettings(c PostgresConfig) (*pgxpool.Config, time.Duration, error) {
	if !protocol.ValidID(c.ConnectionStringEnv) || c.MaxConnections < 0 || c.MaxConnections > 16 || c.QueryTimeoutMilliseconds > 15000 {
		return nil, 0, fmt.Errorf("invalid local PostgreSQL settings")
	}
	dsn := os.Getenv(c.ConnectionStringEnv)
	if strings.TrimSpace(dsn) == "" {
		return nil, 0, fmt.Errorf("explicit PostgreSQL connection environment variable is empty")
	}
	cfg, e := pgxpool.ParseConfig(dsn)
	if e != nil {
		return nil, 0, fmt.Errorf("invalid PostgreSQL connection settings")
	}
	validHost := func(host string) bool {
		if filepath.IsAbs(host) {
			return filepath.Clean(host) == host
		}
		ip := net.ParseIP(host)
		return ip != nil && ip.IsLoopback()
	}
	if !validHost(cfg.ConnConfig.Host) {
		return nil, 0, fmt.Errorf("PostgreSQL development connection must use an absolute Unix socket directory or literal loopback")
	}
	for _, f := range cfg.ConnConfig.Fallbacks {
		if !validHost(f.Host) {
			return nil, 0, fmt.Errorf("nonlocal PostgreSQL fallback rejected")
		}
	}
	timeout := time.Duration(c.QueryTimeoutMilliseconds) * time.Millisecond
	if timeout == 0 {
		timeout = 5 * time.Second
	}
	if timeout < 100*time.Millisecond {
		return nil, 0, fmt.Errorf("PostgreSQL timeout must be 100..15000 milliseconds")
	}
	cfg.MaxConns = c.MaxConnections
	if cfg.MaxConns == 0 {
		cfg.MaxConns = 4
	}
	cfg.MinConns = 0
	cfg.ConnConfig.ConnectTimeout = 2 * time.Second
	cfg.ConnConfig.RuntimeParams = map[string]string{"application_name": "mixer-local-release", "search_path": "pg_catalog", "statement_timeout": strconv.FormatInt(timeout.Milliseconds(), 10), "lock_timeout": strconv.FormatInt(timeout.Milliseconds(), 10), "idle_in_transaction_session_timeout": strconv.FormatInt(timeout.Milliseconds()+1000, 10), "synchronous_commit": "on", "row_security": "on"}
	cfg.ConnConfig.MaxProtocolMessageBodyLen = 20 * 1024 * 1024
	return cfg, timeout, nil
}

// MigratePostgres applies reviewed embedded migrations using separate owner
// credentials. It never creates a login or grants runtime credentials membership.
func MigratePostgres(ctx context.Context, c PostgresConfig) error {
	cfg, timeout, e := postgresSettings(c)
	if e != nil {
		return e
	}
	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()
	conn, e := pgx.ConnectConfig(ctx, cfg.ConnConfig)
	if e != nil {
		return storageError()
	}
	defer closePostgres(conn)
	tx, e := conn.Begin(ctx)
	if e != nil {
		return storageError()
	}
	defer rollbackPostgres(tx)
	if _, e = tx.Exec(ctx, "SELECT pg_advisory_xact_lock(1716594471)"); e != nil {
		return storageError()
	}
	var existing *string
	if e = tx.QueryRow(ctx, "SELECT to_regclass('mixer_release.schema_migrations')::text").Scan(&existing); e != nil {
		return storageError()
	}
	migration, _ := migrations.ReadFile("migrations/001_release.sql")
	checksum := protocol.Hash(migration)
	if existing != nil {
		var count, version int
		var hash string
		if e = tx.QueryRow(ctx, "SELECT count(*),coalesce(min(version),0),coalesce(min(checksum),'') FROM mixer_release.schema_migrations").Scan(&count, &version, &hash); e != nil || count != 1 || version != 1 || hash != checksum {
			return fmt.Errorf("PostgreSQL migration version/checksum mismatch")
		}
	} else {
		if _, e = tx.Exec(ctx, string(migration)); e != nil {
			return fmt.Errorf("PostgreSQL migration failed; no schema changes committed")
		}
		if _, e = tx.Exec(ctx, "CREATE TABLE mixer_release.schema_migrations(version integer PRIMARY KEY CHECK(version=1),checksum text NOT NULL CHECK(checksum ~ '^[a-f0-9]{64}$')); REVOKE ALL ON mixer_release.schema_migrations FROM PUBLIC; GRANT SELECT ON mixer_release.schema_migrations TO mixer_release_runtime"); e != nil {
			return storageError()
		}
		if _, e = tx.Exec(ctx, "INSERT INTO mixer_release.schema_migrations(version,checksum) VALUES(1,$1)", checksum); e != nil {
			return storageError()
		}
	}
	if e = tx.Commit(ctx); e != nil {
		return storageError()
	}
	return nil
}
func openPostgres(c PostgresConfig, fault durable.Fault) (*postgresStore, error) {
	cfg, timeout, e := postgresSettings(c)
	if e != nil {
		return nil, e
	}
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()
	pool, e := pgxpool.NewWithConfig(ctx, cfg)
	if e != nil {
		return nil, storageError()
	}
	success := false
	defer func() {
		if !success {
			pool.Close()
		}
	}()
	var unsafe, member, owner bool
	// MEMBER alone is too broad on PostgreSQL16+: an INHERIT/SET-disabled
	// membership need not confer authority. ADMIN OPTION can enable it again,
	// including through inherited/assumable administrator roles and admin chains.
	// Before16 every membership permits SET ROLE, so MEMBER is the correct test.
	e = pool.QueryRow(ctx, `WITH RECURSIVE
 settings AS (SELECT CASE WHEN current_setting('server_version_num')::integer>=160000 THEN 'SET' ELSE 'MEMBER' END AS assume_privilege),
 role_access AS (
  SELECT r.oid,pg_has_role(current_user,r.oid,'USAGE') AS inherited,
   pg_has_role(current_user,r.oid,(SELECT assume_privilege FROM settings)) AS assumable
  FROM pg_roles r
 ),
 admin_roles(oid) AS (
  SELECT m.roleid FROM pg_auth_members m JOIN role_access a ON a.oid=m.member
   WHERE m.admin_option AND (a.inherited OR a.assumable)
  UNION
  SELECT m.roleid FROM admin_roles a JOIN pg_roles r
   ON pg_has_role(a.oid,r.oid,'USAGE') OR pg_has_role(a.oid,r.oid,(SELECT assume_privilege FROM settings))
   JOIN pg_auth_members m ON m.member=r.oid AND m.admin_option
 ),
 effective_access AS (
  SELECT r.oid,
   r.inherited OR r.assumable OR EXISTS(SELECT 1 FROM admin_roles a WHERE pg_has_role(a.oid,r.oid,'USAGE') OR pg_has_role(a.oid,r.oid,(SELECT assume_privilege FROM settings))) AS usable,
   r.assumable OR EXISTS(SELECT 1 FROM admin_roles a WHERE pg_has_role(a.oid,r.oid,(SELECT assume_privilege FROM settings))) AS assumable
  FROM role_access r
 ),
 release_owners(oid) AS (
  SELECT c.relowner FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='mixer_release'
  UNION SELECT n.nspowner FROM pg_namespace n WHERE n.nspname='mixer_release'
  UNION SELECT p.proowner FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='mixer_release'
 )
 SELECT
 EXISTS(SELECT 1 FROM pg_roles r JOIN effective_access a ON a.oid=r.oid WHERE (r.rolsuper OR r.rolbypassrls OR r.rolcreaterole OR r.rolcreatedb) AND a.assumable),
 pg_has_role(current_user,'mixer_release_runtime','USAGE'),
 EXISTS(SELECT 1 FROM release_owners o JOIN effective_access a ON a.oid=o.oid WHERE a.usable)`).Scan(&unsafe, &member, &owner)
	if e != nil {
		return nil, storageError()
	}
	if unsafe || !member || owner {
		return nil, fmt.Errorf("PostgreSQL runtime requires a non-owner role without superuser, create-role/database or RLS bypass authority")
	}
	var tables int
	var fsync, fullPages, commit, version string
	if e = pool.QueryRow(ctx, "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='mixer_release' AND c.relname IN ('tenant_heads','artifacts','artifact_state','assignments','channel_heads','idempotency','audit_events','outbox') AND c.relrowsecurity AND c.relforcerowsecurity").Scan(&tables); e != nil {
		return nil, storageError()
	}
	if e = pool.QueryRow(ctx, "SELECT current_setting('fsync'),current_setting('full_page_writes'),current_setting('synchronous_commit'),current_setting('server_version_num')").Scan(&fsync, &fullPages, &commit, &version); e != nil {
		return nil, storageError()
	}
	number, _ := strconv.Atoi(version)
	if tables != 8 || fsync != "on" || fullPages != "on" || commit != "on" || number < 140000 {
		return nil, fmt.Errorf("PostgreSQL schema/RLS or durable-write prerequisites missing")
	}
	migration, _ := migrations.ReadFile("migrations/001_release.sql")
	var count, migrationVersion int
	var checksum string
	if e = pool.QueryRow(ctx, "SELECT count(*),coalesce(min(version),0),coalesce(min(checksum),'') FROM mixer_release.schema_migrations").Scan(&count, &migrationVersion, &checksum); e != nil {
		return nil, storageError()
	}
	if count != 1 || migrationVersion != 1 || checksum != protocol.Hash(migration) {
		return nil, fmt.Errorf("PostgreSQL migration version/checksum mismatch")
	}
	success = true
	return &postgresStore{pool: pool, timeout: timeout, fault: fault}, nil
}
func (s *postgresStore) close() error { s.pool.Close(); return nil }
func (s *postgresStore) begin(ctx context.Context, t tenant, role string) (pgx.Tx, context.Context, context.CancelFunc, error) {
	ctx, cancel := context.WithTimeout(ctx, s.timeout)
	if !t.valid() {
		cancel()
		return nil, ctx, func() {}, apiError{403, "scope_denied", "invalid storage tenant"}
	}
	tx, e := s.pool.Begin(ctx)
	if e != nil {
		cancel()
		return nil, ctx, func() {}, storageError()
	}
	if _, e = tx.Exec(ctx, "SELECT set_config('mixer.organization',$1,true),set_config('mixer.project',$2,true),set_config('mixer.role',$3,true)", t.Organization, t.Project, role); e != nil {
		rollbackPostgres(tx)
		cancel()
		return nil, ctx, func() {}, storageError()
	}
	return tx, ctx, cancel, nil
}
func (s *postgresStore) transaction(ctx context.Context, who access, role, key, hash string, event Event, fn func(releaseTransaction) (Response, error)) (Response, error) {
	if e := who.require(role); e != nil {
		return Response{}, e
	}
	if !protocol.ValidID(key) || !protocol.ValidDigest(hash) || event.Organization != who.Organization || event.Project != who.Project || event.Actor != who.Actor {
		return Response{}, apiError{403, "scope_denied", "invalid authenticated transaction scope"}
	}
	tx, ctx, cancel, e := s.begin(ctx, who.tenant, who.Role)
	if e != nil {
		return Response{}, e
	}
	defer cancel()
	defer rollbackPostgres(tx)
	initial := protocol.Hash([]byte("mixer.release.tenant-state.v1"))
	if _, e = tx.Exec(ctx, "INSERT INTO mixer_release.tenant_heads(organization,project,state_hash) VALUES($1,$2,$3) ON CONFLICT DO NOTHING", who.Organization, who.Project, initial); e != nil {
		return Response{}, storageError()
	}
	var lastText, previousHash, stateHash string
	if e = tx.QueryRow(ctx, "SELECT last_event::text,audit_hash,state_hash FROM mixer_release.tenant_heads WHERE organization=$1 AND project=$2 FOR UPDATE", who.Organization, who.Project).Scan(&lastText, &previousHash, &stateHash); e != nil {
		return Response{}, storageError()
	}
	last, e := strconv.ParseUint(lastText, 10, 64)
	if e != nil || last == ^uint64(0) {
		return Response{}, storageError()
	}
	if last == 0 {
		if previousHash != "" || stateHash != initial {
			return Response{}, storageError()
		}
	} else {
		var raw []byte
		var hash string
		if e = tx.QueryRow(ctx, "SELECT event_body,event_hash FROM mixer_release.audit_events WHERE organization=$1 AND project=$2 AND id=$3", who.Organization, who.Project, lastText).Scan(&raw, &hash); e != nil {
			return Response{}, storageError()
		}
		prior, valid := verifyStoredEvent(raw, who.tenant, last)
		if !valid || prior.Hash != previousHash || hash != previousHash || prior.Current != stateHash {
			return Response{}, storageError()
		}
	}
	var oldHash string
	var result Response
	e = tx.QueryRow(ctx, "SELECT request_hash,status,response_body FROM mixer_release.idempotency WHERE organization=$1 AND project=$2 AND key=$3", who.Organization, who.Project, key).Scan(&oldHash, &result.Status, &result.Body)
	if e == nil {
		if oldHash != hash {
			return Response{}, apiError{409, "idempotency_conflict", "key was already used for another request"}
		}
		return result, nil
	}
	if !errors.Is(e, pgx.ErrNoRows) {
		return Response{}, storageError()
	}
	current := &postgresTransaction{tx: tx, ctx: ctx, who: who, changes: []domainChange{}}
	result, e = fn(current)
	if e != nil {
		return Response{}, e
	}
	event.ID = last + 1
	event.PreviousHash = previousHash
	event.Previous = stateHash
	event.Current = stateHash
	if len(current.changes) > 0 {
		b, _ := json.Marshal(struct {
			Previous string         `json:"previous"`
			Changes  []domainChange `json:"changes"`
		}{stateHash, current.changes})
		event.Current = protocol.Hash(b)
	}
	event.Hash = ""
	canonical, _ := json.Marshal(event)
	event.Hash = protocol.Hash(canonical)
	eventBytes, _ := json.Marshal(event)
	workBytes, _ := json.Marshal(Work{ID: event.ID, EventID: event.ID, Kind: event.Action, Status: "pending_local_only", RequestID: event.RequestID})
	id := strconv.FormatUint(event.ID, 10)
	if _, e = tx.Exec(ctx, "INSERT INTO mixer_release.audit_events(organization,project,id,event_body,event_hash,previous_hash) VALUES($1,$2,$3,$4,$5,$6)", who.Organization, who.Project, id, eventBytes, event.Hash, event.PreviousHash); e != nil {
		return Response{}, storageError()
	}
	if _, e = tx.Exec(ctx, "INSERT INTO mixer_release.outbox(organization,project,id,event_id,work_body) VALUES($1,$2,$3,$3,$4)", who.Organization, who.Project, id, workBytes); e != nil {
		return Response{}, storageError()
	}
	if _, e = tx.Exec(ctx, "INSERT INTO mixer_release.idempotency(organization,project,key,request_hash,status,response_body) VALUES($1,$2,$3,$4,$5,$6)", who.Organization, who.Project, key, hash, result.Status, []byte(result.Body)); e != nil {
		return Response{}, storageError()
	}
	if _, e = tx.Exec(ctx, "UPDATE mixer_release.tenant_heads SET last_event=$3,audit_hash=$4,state_hash=$5 WHERE organization=$1 AND project=$2", who.Organization, who.Project, id, event.Hash, event.Current); e != nil {
		return Response{}, storageError()
	}
	if s.fault != nil {
		if e = s.fault("postgres_before_commit"); e != nil {
			return Response{}, storageError()
		}
	}
	if e = tx.Commit(ctx); e != nil {
		return Response{}, storageError()
	}
	if s.fault != nil {
		if e = s.fault("postgres_after_commit"); e != nil {
			return Response{}, storageError()
		}
	}
	return result, nil
}

type domainChange struct {
	Kind   string `json:"kind"`
	Key    string `json:"key"`
	Before string `json:"before"`
	After  string `json:"after"`
}
type postgresTransaction struct {
	tx      pgx.Tx
	ctx     context.Context
	who     access
	changes []domainChange
}

func valueHash(v any) string { b, _ := json.Marshal(v); return protocol.Hash(b) }
func verifyStoredEvent(raw []byte, scope tenant, id uint64) (Event, bool) {
	var event Event
	if protocol.DecodeJSON(raw, &event) != nil {
		return Event{}, false
	}
	hash := event.Hash
	event.Hash = ""
	canonical, _ := json.Marshal(event)
	event.Hash = hash
	return event, event.ID == id && event.Organization == scope.Organization && event.Project == scope.Project && protocol.ValidDigest(event.Previous) && protocol.ValidDigest(event.Current) && event.Hash == protocol.Hash(canonical)
}
func (t *postgresTransaction) artifact(digest string) (Record, bool, error) {
	return queryArtifact(t.ctx, t.tx, t.who.tenant, digest, false)
}
func queryArtifact(ctx context.Context, tx pgx.Tx, scope tenant, digest string, published bool) (Record, bool, error) {
	if !protocol.ValidDigest(digest) {
		return Record{}, false, nil
	}
	var manifest, payload []byte
	var validated, visible bool
	e := tx.QueryRow(ctx, `SELECT a.signed_manifest,a.payload,s.validated,s.published FROM mixer_release.artifacts a JOIN mixer_release.artifact_state s USING(organization,project,digest) WHERE a.organization=$1 AND a.project=$2 AND a.digest=$3 AND (NOT $4::boolean OR s.published)`, scope.Organization, scope.Project, digest, published).Scan(&manifest, &payload, &validated, &visible)
	if errors.Is(e, pgx.ErrNoRows) {
		return Record{}, false, nil
	}
	if e != nil {
		return Record{}, false, storageError()
	}
	record, e := decodeStoredArtifact(manifest, payload)
	record.Validated, record.Published = validated, visible
	if e != nil || checkArtifact(scope, digest, record) != nil {
		return Record{}, false, storageError()
	}
	return record, true, nil
}
func (t *postgresTransaction) saveArtifact(digest string, record Record) error {
	if e := t.who.require("editor"); e != nil {
		return e
	}
	if e := checkArtifact(t.who.tenant, digest, record); e != nil {
		return e
	}
	old, exists, e := t.artifact(digest)
	if e != nil {
		return e
	}
	before := ""
	if exists {
		if !immutableEqual(old, record) {
			return apiError{409, "immutable_conflict", "artifact content is immutable"}
		}
		if old.Published && !record.Published || old.Validated && !record.Validated {
			return apiError{409, "immutable_conflict", "artifact state cannot move backwards"}
		}
		if old.Published != record.Published {
			if e = t.who.require("publisher"); e != nil {
				return e
			}
		}
		before = valueHash(old)
	} else {
		if record.Published {
			if e = t.who.require("publisher"); e != nil {
				return e
			}
		}
		var count int
		if e = t.tx.QueryRow(t.ctx, "SELECT count(*) FROM (SELECT 1 FROM mixer_release.artifacts WHERE organization=$1 AND project=$2 LIMIT 64) a", t.who.Organization, t.who.Project).Scan(&count); e != nil {
			return storageError()
		}
		if count >= 64 {
			return apiError{409, "local_capacity", "development tenant artifact limit reached"}
		}
		manifest, _ := json.Marshal(record.signedManifest())
		if _, e = t.tx.Exec(t.ctx, "INSERT INTO mixer_release.artifacts(organization,project,digest,signed_manifest,payload) VALUES($1,$2,$3,$4,$5)", t.who.Organization, t.who.Project, digest, manifest, record.payload()); e != nil {
			return storageError()
		}
	}
	if _, e = t.tx.Exec(t.ctx, "INSERT INTO mixer_release.artifact_state(organization,project,digest,validated,published) VALUES($1,$2,$3,$4,$5) ON CONFLICT(organization,project,digest) DO UPDATE SET validated=EXCLUDED.validated,published=EXCLUDED.published", t.who.Organization, t.who.Project, digest, record.Validated, record.Published); e != nil {
		return storageError()
	}
	after := valueHash(record)
	if before != after {
		t.changes = append(t.changes, domainChange{"artifact", digest, before, after})
	}
	return nil
}
func queryChannel(ctx context.Context, tx pgx.Tx, scope tenant, key string) (Channel, bool, error) {
	if !strings.HasPrefix(key, scope.prefix()) || len(key) > 1024 {
		return Channel{}, false, apiError{403, "scope_denied", "channel storage scope differs"}
	}
	var raw []byte
	e := tx.QueryRow(ctx, "SELECT a.signed_assignment FROM mixer_release.channel_heads h JOIN mixer_release.assignments a USING(organization,project,channel_key,sequence) WHERE h.organization=$1 AND h.project=$2 AND h.channel_key=$3", scope.Organization, scope.Project, key).Scan(&raw)
	if errors.Is(e, pgx.ErrNoRows) {
		return Channel{}, false, nil
	}
	if e != nil {
		return Channel{}, false, storageError()
	}
	channel, decodeError := decodeStoredChannel(raw)
	if decodeError != nil {
		return Channel{}, false, storageError()
	}
	if checkChannel(scope, key, channel) != nil {
		return Channel{}, false, storageError()
	}
	return channel, true, nil
}
func (t *postgresTransaction) channel(key string) (Channel, bool, error) {
	return queryChannel(t.ctx, t.tx, t.who.tenant, key)
}
func (t *postgresTransaction) saveChannel(key string, channel Channel) error {
	if e := t.who.require("publisher"); e != nil {
		return e
	}
	if e := checkChannel(t.who.tenant, key, channel); e != nil {
		return e
	}
	artifact, found, e := t.artifact(channel.assignment().ArtifactSHA256)
	if e != nil {
		return e
	}
	if !found || checkChannelArtifact(artifact, channel) != nil {
		return apiError{422, "assignment_invalid", "assignment artifact binding rejected"}
	}
	old, exists, e := t.channel(key)
	if e != nil {
		return e
	}
	before := ""
	a := channel.assignment()
	if exists {
		if channel.version() != old.version() || a.Sequence <= old.assignment().Sequence {
			return apiError{409, "assignment_rejected", "assignment sequence must increase"}
		}
		before = valueHash(old)
	}
	raw, _ := json.Marshal(channel.wire())
	sequence := strconv.FormatUint(a.Sequence, 10)
	if _, e = t.tx.Exec(t.ctx, "INSERT INTO mixer_release.assignments(organization,project,channel_key,sequence,artifact_digest,signed_assignment) VALUES($1,$2,$3,$4,$5,$6)", t.who.Organization, t.who.Project, key, sequence, a.ArtifactSHA256, raw); e != nil {
		return storageError()
	}
	if _, e = t.tx.Exec(t.ctx, "INSERT INTO mixer_release.channel_heads(organization,project,channel_key,sequence) VALUES($1,$2,$3,$4) ON CONFLICT(organization,project,channel_key) DO UPDATE SET sequence=EXCLUDED.sequence", t.who.Organization, t.who.Project, key, sequence); e != nil {
		return storageError()
	}
	t.changes = append(t.changes, domainChange{"channel", key, before, valueHash(channel)})
	return nil
}
func (s *postgresStore) artifact(ctx context.Context, who access, digest string) (Record, bool, error) {
	if e := who.require("reader"); e != nil {
		return Record{}, false, e
	}
	tx, ctx, cancel, e := s.begin(ctx, who.tenant, who.Role)
	if e != nil {
		return Record{}, false, e
	}
	defer cancel()
	defer rollbackPostgres(tx)
	return queryArtifact(ctx, tx, who.tenant, digest, false)
}
func (s *postgresStore) publicArtifact(ctx context.Context, scope tenant, digest string) (Record, bool, error) {
	tx, ctx, cancel, e := s.begin(ctx, scope, "delivery")
	if e != nil {
		return Record{}, false, e
	}
	defer cancel()
	defer rollbackPostgres(tx)
	return queryArtifact(ctx, tx, scope, digest, true)
}
func (s *postgresStore) publicChannel(ctx context.Context, scope tenant, key string) (Channel, bool, error) {
	tx, ctx, cancel, e := s.begin(ctx, scope, "delivery")
	if e != nil {
		return Channel{}, false, e
	}
	defer cancel()
	defer rollbackPostgres(tx)
	return queryChannel(ctx, tx, scope, key)
}
func (s *postgresStore) history(ctx context.Context, who access, after uint64, limit int) ([]Event, []Work, uint64, error) {
	if e := who.require("reader"); e != nil {
		return nil, nil, after, e
	}
	if limit < 1 || limit > 100 {
		return nil, nil, after, apiError{400, "invalid_limit", "limit must be 1..100"}
	}
	tx, ctx, cancel, e := s.begin(ctx, who.tenant, who.Role)
	if e != nil {
		return nil, nil, after, e
	}
	defer cancel()
	defer rollbackPostgres(tx)
	previous := ""
	previousState := ""
	if after > 0 {
		var raw []byte
		var id string
		e = tx.QueryRow(ctx, "SELECT id::text,event_body FROM mixer_release.audit_events WHERE organization=$1 AND project=$2 AND id<=$3 ORDER BY id DESC LIMIT 1", who.Organization, who.Project, strconv.FormatUint(after, 10)).Scan(&id, &raw)
		if e != nil && !errors.Is(e, pgx.ErrNoRows) {
			return nil, nil, after, storageError()
		}
		if e == nil {
			number, err := strconv.ParseUint(id, 10, 64)
			prior, valid := verifyStoredEvent(raw, who.tenant, number)
			if err != nil || !valid {
				return nil, nil, after, storageError()
			}
			previous = prior.Hash
			previousState = prior.Current
		}
	}
	rows, e := tx.Query(ctx, "SELECT a.id::text,a.event_body,o.work_body FROM mixer_release.audit_events a JOIN mixer_release.outbox o ON o.organization=a.organization AND o.project=a.project AND o.event_id=a.id WHERE a.organization=$1 AND a.project=$2 AND a.id>$3 ORDER BY a.id LIMIT $4", who.Organization, who.Project, strconv.FormatUint(after, 10), limit)
	if e != nil {
		return nil, nil, after, storageError()
	}
	defer rows.Close()
	events := []Event{}
	work := []Work{}
	next := after
	for rows.Next() {
		var id string
		var eventBytes, workBytes []byte
		if e = rows.Scan(&id, &eventBytes, &workBytes); e != nil {
			return nil, nil, after, storageError()
		}
		var event Event
		var item Work
		if protocol.DecodeJSON(eventBytes, &event) != nil || protocol.DecodeJSON(workBytes, &item) != nil {
			return nil, nil, after, storageError()
		}
		number, e := strconv.ParseUint(id, 10, 64)
		if e != nil {
			return nil, nil, after, storageError()
		}
		event, valid := verifyStoredEvent(eventBytes, who.tenant, number)
		if !valid || event.ID != next+1 || event.PreviousHash != previous || previousState != "" && event.Previous != previousState || item.EventID != event.ID || item.ID != event.ID || item.Status != "pending_local_only" {
			return nil, nil, after, storageError()
		}
		events = append(events, event)
		work = append(work, item)
		next = event.ID
		previous = event.Hash
		previousState = event.Current
	}
	if rows.Err() != nil {
		return nil, nil, after, storageError()
	}
	return events, work, next, nil
}
