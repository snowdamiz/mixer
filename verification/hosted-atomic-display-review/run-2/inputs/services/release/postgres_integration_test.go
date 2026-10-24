//go:build postgres_integration

package release

import (
	"bytes"
	"context"
	"crypto/rand"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"syscall"
	"testing"
	"time"

	"github.com/jackc/pgx/v5"
	"mixer/services/internal/durable"
	"mixer/services/internal/testutil"
	"mixer/services/protocol"
)

func isolatedOwner(t *testing.T) (*pgx.Conn, string) {
	t.Helper()
	dsn := os.Getenv("MIXER_TEST_POSTGRES_OWNER")
	data := os.Getenv("MIXER_TEST_POSTGRES_DATA_DIRECTORY")
	if dsn == "" || data == "" || !strings.HasPrefix(filepath.Base(filepath.Dir(data)), "mixer-pg-") {
		t.Fatal("real PostgreSQL test requires the dedicated isolated cluster runner")
	}
	if marker, e := os.ReadFile(filepath.Join(filepath.Dir(data), "mixer-test-cluster")); e != nil || string(marker) != "original-mixer-postgres-tests\n" {
		t.Fatal("isolated test cluster marker missing")
	}
	conn, e := pgx.Connect(context.Background(), dsn)
	if e != nil {
		t.Fatal("isolated PostgreSQL unavailable")
	}
	var actual string
	var listen, version string
	if e = conn.QueryRow(context.Background(), "SELECT current_setting('data_directory'),current_setting('listen_addresses'),version()").Scan(&actual, &listen, &version); e != nil || actual != data || listen != "" {
		conn.Close(context.Background())
		t.Fatal("refusing database outside isolated test cluster")
	}
	t.Log(version + "; verified private data directory and disabled TCP listener")
	return conn, dsn
}
func pgFixture(t *testing.T) (Config, testutil.Fixture, *pgx.Conn, string) {
	t.Helper()
	admin, dsn := isolatedOwner(t)
	t.Cleanup(func() { admin.Close(context.Background()) })
	var random [8]byte
	rand.Read(random[:])
	name := "test_" + fmt.Sprintf("%x", random[:])
	if _, e := admin.Exec(context.Background(), "CREATE DATABASE "+pgx.Identifier{name}.Sanitize()); e != nil {
		t.Fatal(e)
	}
	parsed, e := pgx.ParseConfig(dsn)
	if e != nil {
		t.Fatal(e)
	}
	parsed.Database = name
	owner, e := pgx.ConnectConfig(context.Background(), parsed)
	if e != nil {
		t.Fatal(e)
	}
	t.Cleanup(func() { owner.Close(context.Background()) })
	ownerDSN := fmt.Sprintf("host=%s port=%d dbname=%s user=%s sslmode=disable", parsed.Host, parsed.Port, name, parsed.User)
	envName := "MIXER_PG_TEST_" + strings.ToUpper(fmt.Sprintf("%x", random[:]))
	t.Setenv(envName, ownerDSN)
	pc := PostgresConfig{ConnectionStringEnv: envName, MaxConnections: 4, QueryTimeoutMilliseconds: 5000}
	if e = MigratePostgres(context.Background(), pc); e != nil {
		t.Fatal(e)
	}
	if e = MigratePostgres(context.Background(), pc); e != nil {
		t.Fatal("migration retry", e)
	}
	if _, e = admin.Exec(context.Background(), `DO $$ BEGIN IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='mixer_test_runtime') THEN CREATE ROLE mixer_test_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS; END IF; END $$; GRANT mixer_release_runtime TO mixer_test_runtime`); e != nil {
		t.Fatal(e)
	}
	runtimeDSN := fmt.Sprintf("host=%s port=%d dbname=%s user=mixer_test_runtime sslmode=disable", parsed.Host, parsed.Port, name)
	t.Setenv(envName, runtimeDSN)
	f := testutil.New(t)
	cfg := Config{DeveloperMode: true, Listen: "127.0.0.1:0", StorageBackend: "postgres", Postgres: &pc, Hosts: []protocol.Host{f.Host}, Roots: f.Roots, Tokens: []Token{
		{SHA256: protocol.Hash([]byte("pg publisher")), Role: "publisher", Organization: "org-a", Project: "project-a", Actor: "publisher"},
		{SHA256: protocol.Hash([]byte("pg reader")), Role: "reader", Organization: "org-a", Project: "project-a", Actor: "reader"},
		{SHA256: protocol.Hash([]byte("pg editor")), Role: "editor", Organization: "org-a", Project: "project-a", Actor: "editor"},
		{SHA256: protocol.Hash([]byte("pg tenant b")), Role: "publisher", Organization: "org-b", Project: "project-b", Actor: "publisher-b"}}}
	return cfg, f, owner, ownerDSN
}

const pgBase = "/v1/orgs/org-a/projects/project-a"

func pgRequest(handler http.Handler, method, path, key, token string, value any) *httptest.ResponseRecorder {
	var raw []byte
	if value != nil {
		raw, _ = json.Marshal(value)
	}
	request := httptest.NewRequest(method, path, bytes.NewReader(raw))
	request.RemoteAddr = "127.0.0.1:1"
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("Idempotency-Key", key)
	if token != "" {
		request.Header.Set("Authorization", "Bearer "+token)
	}
	result := httptest.NewRecorder()
	handler.ServeHTTP(result, request)
	return result
}
func pgStatus(t *testing.T, result *httptest.ResponseRecorder, want int) {
	t.Helper()
	if result.Code != want {
		t.Fatalf("expected HTTP%d got%d: %s", want, result.Code, result.Body.String())
	}
}
func pgUpload(t *testing.T, s http.Handler, f testutil.Fixture, id string) (Artifact, string) {
	t.Helper()
	payload := []byte("original real PostgreSQL fixture " + id)
	manifest := f.Manifest(t, payload, id)
	digest, _ := protocol.ManifestDigest(manifest.Manifest)
	artifact := Artifact{manifest, payload}
	pgStatus(t, pgRequest(s, "PUT", pgBase+"/artifacts/"+digest, "upload-"+id, "pg publisher", artifact), 201)
	pgStatus(t, pgRequest(s, "POST", pgBase+"/releases/validate", "validate-"+id, "pg publisher", map[string]string{"artifact_sha256": digest}), 200)
	return artifact, digest
}
func pgPublish(s http.Handler, kind, key string, a protocol.SignedAssignment) *httptest.ResponseRecorder {
	return pgRequest(s, "POST", pgBase+"/channels/beta/"+kind, key, "pg publisher", map[string]any{"signed_assignment": a})
}
func pgEvents(t *testing.T, s http.Handler) []Event {
	t.Helper()
	r := pgRequest(s, "GET", pgBase+"/audit", "", "pg reader", nil)
	pgStatus(t, r, 200)
	var out struct {
		Events []Event `json:"events"`
		Next   uint64  `json:"next"`
	}
	if e := protocol.DecodeJSON(r.Body.Bytes(), &out); e != nil {
		t.Fatal(e)
	}
	return out.Events
}
func pgUpdates(f testutil.Fixture) string {
	return "/v1/updates?organization=org-a&project=project-a&app=fieldlog&environment=development&platform=ios&runtime=" + f.Host.Runtime + "&channel=beta&installation=install-1"
}
func pgServer(t *testing.T, cfg Config, fault durable.Fault) *Server {
	t.Helper()
	s, e := NewWithFault(cfg, fault)
	if e != nil {
		t.Fatal(e)
	}
	t.Cleanup(func() { s.Close() })
	return s
}

func TestPostgresHTTPConcurrentSequenceRollbackAndRestart(t *testing.T) {
	cfg, f, owner, _ := pgFixture(t)
	s := pgServer(t, cfg, nil)
	other := pgServer(t, cfg, nil)
	payload := []byte("original concurrent immutable artifact")
	signed := f.Manifest(t, payload, "concurrent")
	digest, _ := protocol.ManifestDigest(signed.Manifest)
	a := Artifact{signed, payload}
	const count = 20
	codes := make(chan int, count)
	var wg sync.WaitGroup
	for i := 0; i < count; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			server := s
			if i%2 == 1 {
				server = other
			}
			codes <- pgRequest(server, "PUT", pgBase+"/artifacts/"+digest, "same-key", "pg publisher", a).Code
		}(i)
	}
	wg.Wait()
	close(codes)
	for code := range codes {
		if code != 201 {
			t.Fatal("concurrent idempotency", code)
		}
	}
	if len(pgEvents(t, s)) != 1 {
		t.Fatal("duplicate idempotency effects")
	}
	bad := a
	bad.Payload = []byte("different")
	pgStatus(t, pgRequest(other, "PUT", pgBase+"/artifacts/"+digest, "same-key", "pg publisher", bad), 409)
	pgStatus(t, pgRequest(other, "POST", pgBase+"/releases/validate", "same-key", "pg publisher", map[string]string{"artifact_sha256": digest}), 409)
	pgStatus(t, pgRequest(other, "PUT", pgBase+"/artifacts/"+digest, "new-key", "pg publisher", bad), 422)
	first := f.Assignment(t, signed.Manifest, 1, 1000)
	pgStatus(t, pgPublish(s, "publish", "publish-1", first), 422)
	pgStatus(t, pgRequest(s, "POST", pgBase+"/releases/validate", "validate", "pg publisher", map[string]string{"artifact_sha256": digest}), 200)
	pgStatus(t, pgPublish(s, "publish", "publish-1", first), 200)
	newer := f.Assignment(t, signed.Manifest, 2, 10000)
	codes = make(chan int, 2)
	for i := 0; i < 2; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			server := s
			if i == 1 {
				server = other
			}
			codes <- pgPublish(server, "promote", "promote-"+strconv.Itoa(i), newer).Code
		}(i)
	}
	wg.Wait()
	close(codes)
	actual := map[int]int{}
	for code := range codes {
		actual[code]++
	}
	if actual[200] != 1 || actual[409] != 1 {
		t.Fatal("sequence not serialized", actual)
	}
	second, _ := pgUpload(t, s, f, "second")
	pgStatus(t, pgPublish(s, "publish", "publish-3", f.Assignment(t, second.SignedManifest.Manifest, 3, 10000)), 200)
	pgStatus(t, pgPublish(s, "rollback", "stale", first), 409)
	rollback := f.Assignment(t, signed.Manifest, 4, 10000)
	r := pgPublish(s, "rollback", "rollback-4", rollback)
	pgStatus(t, r, 200)
	s.Close()
	s = pgServer(t, cfg, nil)
	retry := pgPublish(s, "rollback", "rollback-4", rollback)
	pgStatus(t, retry, 200)
	if retry.Body.String() != r.Body.String() {
		t.Fatal("restart retry changed bytes")
	}
	pgStatus(t, pgPublish(s, "publish", "stale-after-restart", newer), 409)
	r = pgRequest(s, "GET", pgUpdates(f), "", "", nil)
	pgStatus(t, r, 200)
	if !strings.Contains(r.Body.String(), `"sequence":4`) {
		t.Fatal("high water lost")
	}
	pgStatus(t, pgRequest(s, "GET", "/v1/artifacts/"+digest+"?organization=org-a&project=project-a", "", "", nil), 200)
	events := pgEvents(t, s)
	if len(events) != 8 {
		t.Fatalf("audit/outbox count %d", len(events))
	}
	for i, event := range events {
		if event.ID != uint64(i+1) {
			t.Fatal("event sequence gap")
		}
		if i > 0 && event.PreviousHash != events[i-1].Hash {
			t.Fatal("audit chain")
		}
	}
	var assignments, outbox, idempotency int
	if e := owner.QueryRow(context.Background(), "SELECT (SELECT count(*) FROM mixer_release.assignments),(SELECT count(*) FROM mixer_release.outbox),(SELECT count(*) FROM mixer_release.idempotency)").Scan(&assignments, &outbox, &idempotency); e != nil {
		t.Fatal(e)
	}
	if assignments != 4 || outbox != 8 || idempotency != 8 {
		t.Fatal("transaction history mismatch", assignments, outbox, idempotency)
	}
}

func TestPostgresTenantRBACRLSAndImmutableRows(t *testing.T) {
	cfg, f, owner, _ := pgFixture(t)
	bFixture := f
	bFixture.Host.Scope.Organization = "org-b"
	bFixture.Host.Scope.Project = "project-b"
	bRoots := append([]protocol.Root(nil), f.Roots...)
	for i := range bRoots {
		bRoots[i].Scope = bFixture.Host.Scope
		bRoots[i].KeyID += "-b"
	}
	cfg.Hosts = append(cfg.Hosts, bFixture.Host)
	cfg.Roots = append(cfg.Roots, bRoots...)
	s := pgServer(t, cfg, nil)
	a, digest := pgUpload(t, s, f, "tenant")
	bPayload := []byte("other tenant private bytes")
	bManifest := bFixture.Manifest(t, bPayload, "tenant-b").Manifest
	bManifest.KeyID = "artifact-key-b"
	bSigned, e := protocol.SignManifest(bManifest, bFixture.ArtifactKey)
	if e != nil {
		t.Fatal(e)
	}
	bDigest, _ := protocol.ManifestDigest(bManifest)
	pgStatus(t, pgRequest(s, "PUT", "/v1/orgs/org-b/projects/project-b/artifacts/"+bDigest, "upload-tenant", "pg tenant b", Artifact{bSigned, bPayload}), 201)
	pgStatus(t, pgRequest(s, "GET", pgBase+"/audit", "", "", nil), 401)
	pgStatus(t, pgRequest(s, "GET", pgBase+"/audit", "", "pg tenant b", nil), 403)
	pgStatus(t, pgRequest(s, "POST", pgBase+"/channels/beta/publish", "reader-pub", "pg reader", map[string]any{}), 403)
	pgStatus(t, pgRequest(s, "POST", pgBase+"/channels/beta/publish", "editor-pub", "pg editor", map[string]any{}), 403)
	bBase := "/v1/orgs/org-b/projects/project-b"
	pgStatus(t, pgRequest(s, "PUT", bBase+"/artifacts/"+digest, "cross-body", "pg tenant b", a), 403)
	pgStatus(t, pgRequest(s, "GET", bBase+"/artifacts/"+digest, "", "pg tenant b", nil), 404)
	result := pgRequest(s, "GET", bBase+"/audit", "", "pg tenant b", nil)
	pgStatus(t, result, 200)
	if strings.Contains(result.Body.String(), "publisher\"") {
		t.Fatal("cross tenant audit")
	}
	pgStatus(t, pgRequest(s, "GET", "/v1/artifacts/"+digest+"?organization=org-a&project=project-a", "", "", nil), 404)
	store := s.db.(*postgresStore)
	conn, e := store.pool.Acquire(context.Background())
	if e != nil {
		t.Fatal(e)
	}
	defer conn.Release()
	var count int
	if e = conn.QueryRow(context.Background(), "SELECT count(*) FROM mixer_release.artifacts").Scan(&count); e != nil || count != 0 {
		t.Fatal("unscoped query leaked rows", count, e)
	}
	tx, e := conn.Begin(context.Background())
	if e != nil {
		t.Fatal(e)
	}
	if _, e = tx.Exec(context.Background(), "SELECT set_config('mixer.organization','org-b',true),set_config('mixer.project','project-b',true),set_config('mixer.role','publisher',true)"); e != nil {
		t.Fatal(e)
	}
	if e = tx.QueryRow(context.Background(), "SELECT count(*) FROM mixer_release.artifacts WHERE organization='org-a'").Scan(&count); e != nil || count != 0 {
		t.Fatal("RLS tenant leak", e)
	}
	if _, e = tx.Exec(context.Background(), "INSERT INTO mixer_release.tenant_heads(organization,project,state_hash) VALUES('org-a','other-project',$1)", protocol.Hash(nil)); e == nil {
		t.Fatal("cross tenant RLS insert accepted")
	}
	tx.Rollback(context.Background())
	tx, e = conn.Begin(context.Background())
	if e != nil {
		t.Fatal(e)
	}
	tx.Exec(context.Background(), "SELECT set_config('mixer.organization','org-a',true),set_config('mixer.project','project-a',true),set_config('mixer.role','reader',true)")
	resultTag, e := tx.Exec(context.Background(), "UPDATE mixer_release.artifact_state SET validated=true WHERE organization='org-a' AND project='project-a'")
	if e != nil || resultTag.RowsAffected() != 0 {
		t.Fatal("reader mutation accepted", e)
	}
	// RLS reader UPDATE matches zero rows rather than accepting any transition.
	var validated bool
	if e = owner.QueryRow(context.Background(), "SELECT validated FROM mixer_release.artifact_state WHERE digest=$1", digest).Scan(&validated); e != nil || !validated {
		t.Fatal(e)
	}
	tx.Rollback(context.Background())
	// Even the migration owner cannot update or delete immutable artifact/audit data.
	for _, sql := range []string{"UPDATE mixer_release.artifacts SET payload='tampered'::bytea", "DELETE FROM mixer_release.audit_events", "UPDATE mixer_release.idempotency SET status=202"} {
		if _, e = owner.Exec(context.Background(), sql); e == nil {
			t.Fatal("immutable data changed", sql)
		}
	}
	current := access{tenant{"org-a", "project-a"}, "publisher", "publisher"}
	bad := a
	bad.SignedManifest.Manifest.Scope.Organization = "org-b"
	_, e = s.db.transaction(context.Background(), current, "editor", "store-cross", protocol.Hash([]byte("request")), Event{Organization: "org-a", Project: "project-a", Actor: "publisher"}, func(tx releaseTransaction) (Response, error) {
		return response(201, map[string]bool{"ok": true}), tx.saveArtifact(digest, Record{Artifact: bad})
	})
	if e == nil {
		t.Fatal("storage accepted payload tenant as authority")
	}
}

func TestPostgresCommitInterruptionAndActualCrashRecovery(t *testing.T) {
	for _, point := range []string{"postgres_before_commit", "postgres_after_commit", "postgres_database_crash"} {
		t.Run(point, func(t *testing.T) {
			cfg, f, _, _ := pgFixture(t)
			var armed atomic.Bool
			var fired atomic.Bool
			fault := func(p string) error {
				if !armed.Load() || fired.Load() {
					return nil
				}
				if point == p {
					fired.Store(true)
					return syscall.EIO
				}
				if point == "postgres_database_crash" && p == "postgres_before_commit" {
					fired.Store(true)
					ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
					defer cancel()
					cmd := exec.CommandContext(ctx, os.Getenv("MIXER_TEST_PG_CTL"), "-D", os.Getenv("MIXER_TEST_POSTGRES_DATA_DIRECTORY"), "-l", os.Getenv("MIXER_TEST_POSTGRES_LOG"), "-m", "immediate", "-w", "restart")
					if output, e := cmd.CombinedOutput(); e != nil {
						t.Fatalf("isolated PostgreSQL restart failed: %s", output)
					}
					return nil
				}
				return nil
			}
			s := pgServer(t, cfg, fault)
			a, _ := pgUpload(t, s, f, "interrupted")
			signed := f.Assignment(t, a.SignedManifest.Manifest, 1, 10000)
			armed.Store(true)
			pgStatus(t, pgPublish(s, "publish", "uncertain", signed), 503)
			if !fired.Load() {
				t.Fatal("fault did not execute")
			}
			s.Close()
			s = pgServer(t, cfg, nil)
			beforeRetry := 204
			if point == "postgres_after_commit" {
				beforeRetry = 200
			}
			pgStatus(t, pgRequest(s, "GET", pgUpdates(f), "", "", nil), beforeRetry)
			pgStatus(t, pgPublish(s, "publish", "uncertain", signed), 200)
			if len(pgEvents(t, s)) != 3 {
				t.Fatal("partial or duplicate transaction survived interruption")
			}
		})
	}
}

func TestPostgresStartupRolesTimeoutsAndConfig(t *testing.T) {
	cfg, _, owner, ownerDSN := pgFixture(t)
	original := os.Getenv(cfg.Postgres.ConnectionStringEnv)
	t.Setenv(cfg.Postgres.ConnectionStringEnv, ownerDSN)
	if s, e := New(cfg); e == nil {
		s.Close()
		t.Fatal("migration owner accepted as runtime")
	}
	t.Setenv(cfg.Postgres.ConnectionStringEnv, original)
	s := pgServer(t, cfg, nil)
	store := s.db.(*postgresStore)
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Millisecond)
	defer cancel()
	tx, inner, done, e := store.begin(ctx, tenant{"org-a", "project-a"}, "reader")
	if e != nil {
		t.Fatal(e)
	}
	_, e = tx.Exec(inner, "SELECT pg_sleep(2)")
	done()
	tx.Rollback(context.Background())
	if e == nil {
		t.Fatal("query context deadline ignored")
	}
	for _, host := range []string{"192.0.2.1", "localhost", "/tmp/../tmp"} {
		t.Setenv(cfg.Postgres.ConnectionStringEnv, "host="+host+" user=x dbname=x sslmode=disable")
		if _, _, e = postgresSettings(*cfg.Postgres); e == nil {
			t.Fatal("unsafe host accepted", host)
		}
	}
	t.Setenv(cfg.Postgres.ConnectionStringEnv, original)
	cfg.DeveloperMode = false
	if _, e = New(cfg); e == nil {
		t.Fatal("production mode enabled")
	}
	cfg.DeveloperMode = true
	for _, flag := range []string{"BYPASSRLS", "CREATEROLE", "CREATEDB"} {
		if _, e = owner.Exec(context.Background(), "ALTER ROLE mixer_test_runtime "+flag); e != nil {
			t.Fatal(e)
		}
		service, err := New(cfg)
		if _, e = owner.Exec(context.Background(), "ALTER ROLE mixer_test_runtime NO"+flag); e != nil {
			t.Fatal(e)
		}
		if err == nil {
			service.Close()
			t.Fatal("unsafe runtime role accepted", flag)
		}
	}

	// Version/checksum mismatch fails startup without exposing database details.
	if _, e = owner.Exec(context.Background(), "UPDATE mixer_release.schema_migrations SET checksum=$1", protocol.Hash([]byte("unknown"))); e != nil {
		t.Fatal(e)
	}
	if _, e = New(cfg); e == nil {
		t.Fatal("unknown migration accepted")
	}
}

func TestPostgresUint64AssignmentAndLedgerCorruption(t *testing.T) {
	cfg, f, owner, _ := pgFixture(t)
	s := pgServer(t, cfg, nil)
	a, _ := pgUpload(t, s, f, "maximum-sequence")
	signed := f.Assignment(t, a.SignedManifest.Manifest, ^uint64(0), 10000)
	pgStatus(t, pgPublish(s, "publish", "maximum", signed), 200)
	result := pgRequest(s, "GET", pgUpdates(f), "", "", nil)
	pgStatus(t, result, 200)
	if !strings.Contains(result.Body.String(), "18446744073709551615") {
		t.Fatal("uint64 assignment was truncated")
	}
	pgStatus(t, pgPublish(s, "promote", "same-maximum", signed), 409)
	page := pgRequest(s, "GET", pgBase+"/audit?after=1&limit=1", "", "pg reader", nil)
	pgStatus(t, page, 200)
	if !strings.Contains(page.Body.String(), `"next":2`) {
		t.Fatal("bounded audit cursor")
	}
	if _, e := owner.Exec(context.Background(), "UPDATE mixer_release.tenant_heads SET audit_hash=$1 WHERE organization='org-a' AND project='project-a'", protocol.Hash([]byte("corrupt head"))); e != nil {
		t.Fatal(e)
	}
	pgStatus(t, pgPublish(s, "publish", "maximum", signed), 503)
}
func TestPostgresMaximumPayloadBound(t *testing.T) {
	cfg, f, _, _ := pgFixture(t)
	s := pgServer(t, cfg, nil)
	payload := bytes.Repeat([]byte{0x61}, int(protocol.MaxPayloadBytes))
	signed := f.Manifest(t, payload, "maximum-payload")
	digest, _ := protocol.ManifestDigest(signed.Manifest)
	pgStatus(t, pgRequest(s, "PUT", pgBase+"/artifacts/"+digest, "maximum-payload", "pg publisher", Artifact{signed, payload}), 201)
	result := pgRequest(s, "GET", pgBase+"/artifacts/"+digest, "", "pg reader", nil)
	pgStatus(t, result, 200)
	var downloaded Artifact
	if e := protocol.DecodeJSON(result.Body.Bytes(), &downloaded); e != nil || !bytes.Equal(downloaded.Payload, payload) {
		t.Fatal("maximum payload did not round trip", e)
	}
	signed.Manifest.ExpandedBytes++
	signed.Manifest.CompressedBytes++
	pgStatus(t, pgRequest(s, "PUT", pgBase+"/artifacts/"+digest, "over-bound", "pg publisher", Artifact{signed, append(payload, 0x61)}), 422)
}

func TestPostgresLoopbackHTTPDualPlatformDelivery(t *testing.T) {
	cfg, f, _, _ := pgFixture(t)
	android := f.Host
	android.Scope.Platform = "android"
	android.Runtime = protocol.Hash([]byte("android-native-runtime-test"))
	cfg.Hosts = append(cfg.Hosts, android)
	for _, root := range f.Roots {
		root.Scope = android.Scope
		root.KeyID += "-android"
		cfg.Roots = append(cfg.Roots, root)
	}
	s := pgServer(t, cfg, nil)
	network := httptest.NewServer(s)
	defer network.Close()
	client := &http.Client{Timeout: 3 * time.Second}
	call := func(method, path, key, token string, value any, want int) []byte {
		t.Helper()
		var raw []byte
		if value != nil {
			raw, _ = json.Marshal(value)
		}
		r, e := http.NewRequest(method, network.URL+path, bytes.NewReader(raw))
		if e != nil {
			t.Fatal(e)
		}
		r.Header.Set("Content-Type", "application/json")
		r.Header.Set("Idempotency-Key", key)
		if token != "" {
			r.Header.Set("Authorization", "Bearer "+token)
		}
		result, e := client.Do(r)
		if e != nil {
			t.Fatal(e)
		}
		defer result.Body.Close()
		body, e := io.ReadAll(io.LimitReader(result.Body, 64*1024))
		if e != nil || result.StatusCode != want {
			t.Fatalf("loopback HTTP status %d expected %d: %s", result.StatusCode, want, body)
		}
		if result.Header.Get("X-Request-ID") == "" {
			t.Fatal("missing request correlation")
		}
		return body
	}
	call("GET", pgBase+"/audit", "", "", nil, 401)
	for _, host := range cfg.Hosts {
		platform := host.Scope.Platform
		suffix := ""
		if platform == "android" {
			suffix = "-android"
		}
		payload := []byte("original network fixture " + platform)
		m := f.Manifest(t, payload, "network-"+platform).Manifest
		m.Scope = host.Scope
		m.Runtime = host.Runtime
		m.KeyID = "artifact-key" + suffix
		signed, e := protocol.SignManifest(m, f.ArtifactKey)
		if e != nil {
			t.Fatal(e)
		}
		digest, _ := protocol.ManifestDigest(m)
		call("PUT", pgBase+"/artifacts/"+digest, "network-upload-"+platform, "pg publisher", Artifact{signed, payload}, 201)
		call("POST", pgBase+"/releases/validate", "network-validate-"+platform, "pg publisher", map[string]string{"artifact_sha256": digest}, 200)
		a := f.Assignment(t, m, 1, 10000).Assignment
		a.KeyID = "assignment-key" + suffix
		assignment, e := protocol.SignAssignment(a, f.AssignmentKey)
		if e != nil {
			t.Fatal(e)
		}
		body := call("POST", pgBase+"/channels/beta/publish", "network-publish-"+platform, "pg publisher", map[string]any{"signed_assignment": assignment}, 200)
		if !strings.Contains(string(body), `"delivery":"local_only"`) {
			t.Fatal("incorrect publication scope")
		}
		query := url.Values{"organization": {"org-a"}, "project": {"project-a"}, "app": {"fieldlog"}, "environment": {"development"}, "platform": {platform}, "runtime": {host.Runtime}, "channel": {"beta"}, "installation": {"network-installation"}}
		body = call("GET", "/v1/updates?"+query.Encode(), "", "", nil, 200)
		var offered struct {
			SignedAssignment protocol.SignedAssignment `json:"signed_assignment"`
			ArtifactURL      string                    `json:"artifact_url"`
		}
		if protocol.DecodeJSON(body, &offered) != nil || offered.SignedAssignment.Assignment.Scope != host.Scope {
			t.Fatal("wrong platform channel delivery")
		}
		body = call("GET", offered.ArtifactURL, "", "", nil, 200)
		var downloaded Artifact
		if protocol.DecodeJSON(body, &downloaded) != nil || protocol.VerifyManifest(downloaded.SignedManifest, downloaded.Payload, cfg.Roots, host, uint64(time.Now().Unix())) != nil || !bytes.Equal(downloaded.Payload, payload) {
			t.Fatal("network delivery integrity")
		}
	}
	if len(pgEvents(t, s)) != 6 {
		t.Fatal("dual-platform audit transaction count")
	}
}
