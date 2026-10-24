package release

import (
	"context"
	"encoding/json"
	"strings"
	"testing"

	"mixer/services/internal/testutil"
	"mixer/services/protocol"
)

func TestAuthenticatedStoreScopeAndRoleCannotComeFromPayload(t *testing.T) {
	f := testutil.New(t)
	payload := []byte("original scoped store test")
	signed := f.Manifest(t, payload, "scope")
	digest, _ := protocol.ManifestDigest(signed.Manifest)
	record := Record{Artifact: Artifact{signed, payload}}
	db, e := openStore(t.TempDir(), nil)
	if e != nil {
		t.Fatal(e)
	}
	defer db.close()
	who := access{tenant{"org-a", "project-a"}, "actor", "reader"}
	event := Event{Organization: "org-a", Project: "project-a", Actor: "actor"}
	fn := func(tx releaseTransaction) (Response, error) {
		return response(201, map[string]bool{"saved": true}), tx.saveArtifact(digest, record)
	}
	if _, e = db.transaction(context.Background(), who, "editor", "scope", protocol.Hash([]byte("request")), event, fn); e == nil {
		t.Fatal("reader mutated store")
	}
	who.Role = "publisher"
	event.Actor = "forged-actor"
	if _, e = db.transaction(context.Background(), who, "editor", "scope", protocol.Hash([]byte("request")), event, fn); e == nil {
		t.Fatal("forged audit actor accepted")
	}
	event.Actor = "actor"
	record.Artifact.SignedManifest.Manifest.Scope.Organization = "org-b"
	if _, e = db.transaction(context.Background(), who, "editor", "scope", protocol.Hash([]byte("request")), event, fn); e == nil {
		t.Fatal("body selected another tenant")
	}
	if len(db.state.Audit) != 0 || len(db.state.Artifacts) != 0 || len(db.state.Idempotency) != 0 {
		t.Fatal("failed scope/role operation committed effects")
	}
}
func TestAuditCanonicalHashDoesNotDependOnMapInsertionOrder(t *testing.T) {
	left := map[string]string{}
	right := map[string]string{}
	for _, key := range []string{"z", "a", "long-capability"} {
		left[key] = protocol.Hash([]byte(key))
	}
	for _, key := range []string{"long-capability", "a", "z"} {
		right[key] = protocol.Hash([]byte(key))
	}
	if valueHash(left) != valueHash(right) {
		t.Fatal("audit commitment depends on map iteration")
	}
	event := Event{ID: 1, Organization: "org-a", Project: "project-a", Actor: "actor", Previous: protocol.Hash(nil), Current: protocol.Hash([]byte("next"))}
	raw, _ := json.Marshal(event)
	event.Hash = protocol.Hash(raw)
	raw, _ = json.Marshal(event)
	if _, valid := verifyStoredEvent(raw, tenant{"org-a", "project-a"}, 1); !valid {
		t.Fatal("valid canonical event rejected")
	}
	raw = []byte(strings.Replace(string(raw), `"actor":"actor"`, `"actor":"tampered"`, 1))
	if _, valid := verifyStoredEvent(raw, tenant{"org-a", "project-a"}, 1); valid {
		t.Fatal("audit content substitution accepted")
	}
}
func TestPostgresConfigBoundsAndCredentialRedaction(t *testing.T) {
	const env = "MIXER_UNIT_POSTGRES_DSN"
	const secret = "PASSWORD_MUST_NEVER_BE_LOGGED"
	for _, dsn := range []string{"postgres://user:" + secret + "@192.0.2.1/db", "postgres://user:" + secret + "@localhost/db", "postgres://user:" + secret + "@%GG/db", "host=/tmp/../tmp password=" + secret, " "} {
		t.Setenv(env, dsn)
		_, _, e := postgresSettings(PostgresConfig{ConnectionStringEnv: env})
		if e == nil || strings.Contains(e.Error(), secret) {
			t.Fatal("unsafe or credential-bearing settings error")
		}
	}
	t.Setenv(env, "host=/tmp dbname=mixer user=runtime sslmode=disable")
	for _, config := range []PostgresConfig{{ConnectionStringEnv: env, MaxConnections: 17}, {ConnectionStringEnv: env, MaxConnections: -1}, {ConnectionStringEnv: env, QueryTimeoutMilliseconds: 99}, {ConnectionStringEnv: env, QueryTimeoutMilliseconds: 15001}} {
		if _, _, e := postgresSettings(config); e == nil {
			t.Fatal("unbounded PostgreSQL config accepted")
		}
	}
	cfg, timeout, e := postgresSettings(PostgresConfig{ConnectionStringEnv: env})
	if e != nil || cfg.MaxConns != 4 || timeout.Milliseconds() != 5000 {
		t.Fatal("bounded defaults", e)
	}
}
