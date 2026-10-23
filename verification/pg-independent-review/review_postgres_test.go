//go:build postgres_integration

// Independently authored adversarial tests. Copied only into a frozen services
// export by this review's runner; production services sources remain unchanged.
package release

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"sync/atomic"
	"syscall"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgconn"
	"mixer/services/protocol"
)

func TestPostgresReviewRejectsRuntimeSchemaOwnership(t *testing.T) {
	cfg, _, owner, _ := pgFixture(t)
	if _, err := owner.Exec(context.Background(), "ALTER SCHEMA mixer_release OWNER TO mixer_test_runtime"); err != nil {
		t.Fatal(err)
	}
	service, err := New(cfg)
	if err != nil {
		return
	}
	defer service.Close()
	// Demonstrate the unsafe authority in a rollback-only transaction, solely in
	// the runner-created private test database. No release or schema is retained.
	tx, err := service.db.(*postgresStore).pool.Begin(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	defer rollbackPostgres(tx)
	if _, err = tx.Exec(context.Background(), "DROP SCHEMA mixer_release CASCADE"); err != nil {
		t.Fatalf("startup accepted schema owner; could not reproduce DDL authority: %v", err)
	}
	t.Fatal("startup accepted a runtime schema owner able to DROP every release/audit/idempotency/outbox table despite not owning those tables")
}

func TestPostgresReviewRejectsUnknownMigrationVersion(t *testing.T) {
	cfg, _, owner, ownerDSN := pgFixture(t)
	if _, err := owner.Exec(context.Background(), "ALTER TABLE mixer_release.schema_migrations DROP CONSTRAINT schema_migrations_version_check; UPDATE mixer_release.schema_migrations SET version=2"); err != nil {
		t.Fatal(err)
	}
	// This is deliberate owner-side metadata drift. The advertised fail-closed
	// version check must examine version, independently of the unchanged checksum.
	service, err := New(cfg)
	if err == nil {
		service.Close()
		t.Error("runtime startup accepted schema migration version2 with the version1 checksum")
	}
	t.Setenv(cfg.Postgres.ConnectionStringEnv, ownerDSN)
	if err := MigratePostgres(context.Background(), *cfg.Postgres); err == nil {
		t.Error("migration retry accepted schema migration version2 with the version1 checksum")
	}
}

func TestPostgresReviewRejectsRuntimeGuardFunctionOwnership(t *testing.T) {
	cfg, fixture, owner, _ := pgFixture(t)
	initial := pgServer(t, cfg, nil)
	artifact, _ := pgUpload(t, initial, fixture, "review-function-owner")
	pgStatus(t, pgPublish(initial, "publish", "review-function-sequence1", fixture.Assignment(t, artifact.SignedManifest.Manifest, 1, 1000)), 200)
	pgStatus(t, pgPublish(initial, "promote", "review-function-sequence5", fixture.Assignment(t, artifact.SignedManifest.Manifest, 5, 10000)), 200)
	initial.Close()
	if _, err := owner.Exec(context.Background(), "ALTER FUNCTION mixer_release.monotonic_channel() OWNER TO mixer_test_runtime"); err != nil {
		t.Fatal(err)
	}
	service, err := New(cfg)
	if err != nil {
		return
	}
	defer service.Close()
	store := service.db.(*postgresStore)
	// Function ownership permits removing this trigger with DROP ... CASCADE,
	// without CREATE on the schema or table ownership. The installed runtime's
	// existing UPDATE grant then suffices to lower the persisted sequence.
	tx, ctx, cancel, err := store.begin(context.Background(), tenant{"org-a", "project-a"}, "publisher")
	if err != nil {
		t.Fatal(err)
	}
	defer cancel()
	defer rollbackPostgres(tx)
	if _, err := tx.Exec(ctx, "DROP FUNCTION mixer_release.monotonic_channel() CASCADE; UPDATE mixer_release.channel_heads SET sequence=1 WHERE organization='org-a' AND project='project-a'"); err != nil {
		t.Fatalf("accepted function owner; could not reproduce sequence guard removal: %v", err)
	}
	var sequence string
	if err := tx.QueryRow(ctx, "SELECT sequence::text FROM mixer_release.channel_heads WHERE organization='org-a' AND project='project-a'").Scan(&sequence); err != nil {
		t.Fatal(err)
	}
	if sequence != "1" {
		t.Fatalf("accepted function owner; expected sequence5 to be lowered to1, got %s", sequence)
	}
	t.Fatal("startup accepted a runtime guard-function owner able to remove the installed trigger and lower committed sequence5 to1 without CREATE schema or table-owner rights")
}

func TestPostgresReviewDatabaseOwnershipAloneDoesNotOverrideInstalledRLS(t *testing.T) {
	cfg, fixture, owner, _ := pgFixture(t)
	initial := pgServer(t, cfg, nil)
	_, _ = pgUpload(t, initial, fixture, "review-database-owner")
	initial.Close()
	var database string
	if err := owner.QueryRow(context.Background(), "SELECT current_database()").Scan(&database); err != nil {
		t.Fatal(err)
	}
	// The database name is generated solely by pgFixture, not an external input.
	if !strings.HasPrefix(database, "test_") || strings.ContainsAny(database, `";\\`) {
		t.Fatal("unexpected private database identifier")
	}
	if _, err := owner.Exec(context.Background(), `ALTER DATABASE "`+database+`" OWNER TO mixer_test_runtime`); err != nil {
		t.Fatal(err)
	}
	service := pgServer(t, cfg, nil)
	store := service.db.(*postgresStore)
	tx, ctx, cancel, err := store.begin(context.Background(), tenant{"org-b", "project-b"}, "reader")
	if err != nil {
		t.Fatal(err)
	}
	var leaked int
	if err := tx.QueryRow(ctx, "SELECT count(*) FROM mixer_release.artifacts").Scan(&leaked); err != nil || leaked != 0 {
		t.Fatalf("database owner bypassed installed RLS: count%d err%v", leaked, err)
	}
	rollbackPostgres(tx)
	cancel()
	for _, command := range []string{
		"ALTER TABLE mixer_release.artifacts DISABLE ROW LEVEL SECURITY",
		"ALTER SCHEMA mixer_release OWNER TO mixer_test_runtime",
		"ALTER FUNCTION mixer_release.in_scope(text,text) SET mixer.organization='org-a'",
	} {
		_, err := store.pool.Exec(context.Background(), command)
		failure, ok := err.(*pgconn.PgError)
		if !ok || failure.Code != "42501" {
			t.Fatalf("database ownership unexpectedly grants installed-object authority: %s: %v", command, err)
		}
	}
}

func TestPostgresReviewUncertainCommitRetryWithoutRestart(t *testing.T) {
	cfg, fixture, owner, _ := pgFixture(t)
	var failed atomic.Bool
	service := pgServer(t, cfg, func(point string) error {
		if point == "postgres_after_commit" && failed.CompareAndSwap(false, true) {
			return syscall.EIO
		}
		return nil
	})
	other := pgServer(t, cfg, nil)
	payload := []byte("independent lost response retry fixture")
	signed := fixture.Manifest(t, payload, "review-uncertain")
	digest, _ := protocol.ManifestDigest(signed.Manifest)
	artifact := Artifact{signed, payload}
	path := pgBase + "/artifacts/" + digest
	pgStatus(t, pgRequest(service, "PUT", path, "review-lost-response", "pg publisher", artifact), 503)
	if !failed.Load() {
		t.Fatal("after-commit fault was not reached")
	}
	first := pgRequest(other, "PUT", path, "review-lost-response", "pg publisher", artifact)
	pgStatus(t, first, 201)
	for i := 0; i < 10; i++ {
		retry := pgRequest(service, "PUT", path, "review-lost-response", "pg publisher", artifact)
		pgStatus(t, retry, 201)
		if retry.Body.String() != first.Body.String() {
			t.Fatal("live retry changed committed response")
		}
	}
	var artifacts, audit, outbox, keys int
	if err := owner.QueryRow(context.Background(), "SELECT (SELECT count(*) FROM mixer_release.artifacts),(SELECT count(*) FROM mixer_release.audit_events),(SELECT count(*) FROM mixer_release.outbox),(SELECT count(*) FROM mixer_release.idempotency)").Scan(&artifacts, &audit, &outbox, &keys); err != nil {
		t.Fatal(err)
	}
	if artifacts != 1 || audit != 1 || outbox != 1 || keys != 1 {
		t.Fatalf("partial or duplicate commit: %d/%d/%d/%d", artifacts, audit, outbox, keys)
	}
	if len(pgEvents(t, service)) != 1 {
		t.Fatal("retry created extra audit event")
	}
}

func TestPostgresReviewTenantSettingsResetAcrossEveryTable(t *testing.T) {
	cfg, fixture, _, _ := pgFixture(t)
	cfg.Postgres.MaxConnections = 1
	neighbor := fixture
	neighbor.Host.Scope.Project = "project-a-neighbor"
	for _, root := range fixture.Roots {
		root.Scope = neighbor.Host.Scope
		root.KeyID += "-neighbor"
		cfg.Roots = append(cfg.Roots, root)
	}
	cfg.Hosts = append(cfg.Hosts, neighbor.Host)
	cfg.Tokens = append(cfg.Tokens, Token{SHA256: protocol.Hash([]byte("review neighbor")), Role: "publisher", Organization: "org-a", Project: "project-a-neighbor", Actor: "neighbor"})
	service := pgServer(t, cfg, nil)
	a, _ := pgUpload(t, service, fixture, "review-tenant-a")
	pgStatus(t, pgPublish(service, "publish", "review-publish-a", fixture.Assignment(t, a.SignedManifest.Manifest, 1, 10000)), 200)
	payload := []byte("neighbor private payload")
	m := neighbor.Manifest(t, payload, "review-neighbor").Manifest
	m.KeyID += "-neighbor"
	signed, err := protocol.SignManifest(m, neighbor.ArtifactKey)
	if err != nil {
		t.Fatal(err)
	}
	digest, _ := protocol.ManifestDigest(m)
	base := "/v1/orgs/org-a/projects/project-a-neighbor"
	pgStatus(t, pgRequest(service, "PUT", base+"/artifacts/"+digest, "review-neighbor-upload", "review neighbor", Artifact{signed, payload}), 201)
	pgStatus(t, pgRequest(service, "POST", base+"/releases/validate", "review-neighbor-validate", "review neighbor", map[string]string{"artifact_sha256": digest}), 200)
	assignment := neighbor.Assignment(t, m, 1, 10000).Assignment
	assignment.KeyID += "-neighbor"
	signedAssignment, err := protocol.SignAssignment(assignment, neighbor.AssignmentKey)
	if err != nil {
		t.Fatal(err)
	}
	pgStatus(t, pgRequest(service, "POST", base+"/channels/beta/publish", "review-neighbor-publish", "review neighbor", map[string]any{"signed_assignment": signedAssignment}), 200)
	store := service.db.(*postgresStore)
	tables := []string{"tenant_heads", "artifacts", "artifact_state", "assignments", "channel_heads", "idempotency", "audit_events", "outbox"}
	for _, project := range []string{"project-a", "project-a-neighbor", "project-a"} {
		tx, ctx, cancel, err := store.begin(context.Background(), tenant{"org-a", project}, "reader")
		if err != nil {
			t.Fatal(err)
		}
		for _, table := range tables {
			var count, foreign int
			err = tx.QueryRow(ctx, "SELECT count(*),count(*) FILTER(WHERE organization<>'org-a' OR project<>$1) FROM mixer_release."+table, project).Scan(&count, &foreign)
			want := 1
			if table == "idempotency" || table == "audit_events" || table == "outbox" {
				want = 3
			}
			if err != nil || count != want || foreign != 0 {
				t.Fatalf("tenant context leak %s/%s: count%d foreign%d err%v", project, table, count, foreign, err)
			}
		}
		rollbackPostgres(tx)
		cancel()
		for _, table := range tables {
			var count int
			if err := store.pool.QueryRow(context.Background(), "SELECT count(*) FROM mixer_release."+table).Scan(&count); err != nil || count != 0 {
				t.Fatalf("pooled tenant settings survived rollback for %s: count%d err%v", table, count, err)
			}
		}
	}
}

func TestPostgresReviewCancelledLockWaitReservesNothing(t *testing.T) {
	cfg, fixture, owner, _ := pgFixture(t)
	service := pgServer(t, cfg, nil)
	_, digest := pgUpload(t, service, fixture, "review-lock")
	locker, err := owner.Begin(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	defer rollbackPostgres(locker)
	if _, err := locker.Exec(context.Background(), "SELECT 1 FROM mixer_release.tenant_heads WHERE organization='org-a' AND project='project-a' FOR UPDATE"); err != nil {
		t.Fatal(err)
	}
	store := service.db.(*postgresStore)
	ctx, cancel := context.WithTimeout(context.Background(), 40*time.Millisecond)
	defer cancel()
	called := false
	who := access{tenant{"org-a", "project-a"}, "publisher", "publisher"}
	event := Event{Organization: who.Organization, Project: who.Project, Actor: who.Actor, Action: "review bounded cancelled lock"}
	callback := func(tx releaseTransaction) (Response, error) {
		called = true
		_, exists, err := tx.artifact(digest)
		if err != nil || !exists {
			return Response{}, fmt.Errorf("missing committed fixture")
		}
		return response(200, map[string]bool{"ok": true}), nil
	}
	_, err = store.transaction(ctx, who, "editor", "review-cancelled", protocol.Hash([]byte("same cancelled request")), event, callback)
	if err == nil || called {
		t.Fatal("cancelled lock wait executed callback or returned success")
	}
	rollbackPostgres(locker)
	if _, err := store.transaction(context.Background(), who, "editor", "review-cancelled", protocol.Hash([]byte("same cancelled request")), event, callback); err != nil {
		t.Fatal("same-key retry after cancellation failed", err)
	}
	if !called || len(pgEvents(t, service)) != 3 {
		t.Fatal("cancellation reserved idempotency or audit effects")
	}
}

func TestPostgresReviewEveryAppendOnlyFamilyDeniesMutation(t *testing.T) {
	cfg, fixture, owner, _ := pgFixture(t)
	service := pgServer(t, cfg, nil)
	a, _ := pgUpload(t, service, fixture, "review-immutable")
	pgStatus(t, pgPublish(service, "publish", "review-immutable-publish", fixture.Assignment(t, a.SignedManifest.Manifest, 1, 10000)), 200)
	for _, table := range []string{"artifacts", "assignments", "idempotency", "audit_events", "outbox"} {
		_, err := owner.Exec(context.Background(), "DELETE FROM mixer_release."+table)
		failure, ok := err.(*pgconn.PgError)
		if !ok || failure.Code != "42501" {
			t.Fatalf("append-only delete accepted or wrong rejection for %s: %v", table, err)
		}
	}
	if len(pgEvents(t, service)) != 3 {
		t.Fatal("append-only probe altered audit state")
	}
	// Confirm audit and outbox ownership is still the original committed actor,
	// rather than any caller supplied field used during earlier rejected writes.
	rows := pgRequest(service, "GET", pgBase+"/outbox", "", "pg reader", nil)
	pgStatus(t, rows, 200)
	var out struct {
		Work []Work `json:"work"`
		Next uint64 `json:"next"`
	}
	if err := json.Unmarshal(rows.Body.Bytes(), &out); err != nil || len(out.Work) != 3 || out.Next != 3 {
		t.Fatal("outbox history mismatch", err)
	}
	for _, work := range out.Work {
		if !strings.Contains(work.Kind, "/v1/orgs/org-a/projects/project-a/") || work.Status != "pending_local_only" {
			t.Fatal("outbox work changed ownership or delivery state")
		}
	}
}
