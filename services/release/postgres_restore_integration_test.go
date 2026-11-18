//go:build postgres_integration

package release

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"slices"
	"strconv"
	"strings"
	"testing"
	"time"

	"github.com/jackc/pgx/v5"
	"mixer/services/protocol"
)

func TestPostgresReleaseBackupRestore(t *testing.T) {
	cfg, f, owner, _ := pgFixture(t)
	f3 := f.Protocol3()
	cfg.Hosts = append(cfg.Hosts, f3.Host)
	source := pgServer(t, cfg, nil)

	const publisher = "pg publisher"
	const publishKey = "backup-restore-publish"
	artifact, digest := v3Upload(t, source, f3, "backup-restore", publisher)
	assignment := f3.AssignmentV3(t, artifact.SignedManifest.Manifest, 1, 10000)
	published := v3Publish(source, "publish", publishKey, publisher, assignment)
	pgStatus(t, published, http.StatusOK)

	artifactPath := "/v3/artifacts/" + digest
	deliveryPath := artifactPath + "?organization=org-a&project=project-a"
	offerPath := v2OfferPath(f3, 3)
	auditPath := v3Base + "/audit"
	read := func(s *Server, path, token string) []byte {
		t.Helper()
		r := pgRequest(s, "GET", path, "", token, nil)
		pgStatus(t, r, http.StatusOK)
		return r.Body.Bytes()
	}
	auditEvents := func(body []byte) []Event {
		t.Helper()
		var audit struct {
			Events []Event `json:"events"`
			Next   uint64  `json:"next"`
		}
		if err := protocol.DecodeJSON(body, &audit); err != nil {
			t.Fatal(err)
		}
		return audit.Events
	}
	requireBytes := func(label string, got, want []byte) {
		t.Helper()
		if !bytes.Equal(got, want) {
			t.Fatalf("%s bytes differ", label)
		}
	}
	marshal := func(value any) []byte {
		t.Helper()
		raw, err := json.Marshal(value)
		if err != nil {
			t.Fatal(err)
		}
		return raw
	}
	wantArtifact := marshal(artifact)
	wantOffer := marshal(map[string]any{"signed_assignment": assignment, "artifact_url": deliveryPath})
	requireBytes("source artifact", read(source, deliveryPath, ""), wantArtifact)
	requireBytes("source assignment", read(source, offerPath, ""), wantOffer)
	wantAudit := read(source, auditPath, "pg reader")
	events := auditEvents(wantAudit)
	if len(events) != 3 || events[2].Action != "POST "+v3Base+"/channels/beta/publish" {
		t.Fatal("source audit must contain upload, validation and publication")
	}
	if err := source.Close(); err != nil {
		t.Fatal(err)
	}

	// The fixture verified the cluster marker and server identity. Bind libpq
	// to that runner's private socket and select two explicit database names.
	connection := owner.Config()
	socket := filepath.Join(filepath.Dir(os.Getenv("MIXER_TEST_POSTGRES_DATA_DIRECTORY")), "socket")
	if connection.Host != socket || !filepath.IsAbs(socket) {
		t.Fatal("backup and restore require the runner's private Unix socket")
	}
	archive := filepath.Join(t.TempDir(), "release.dump")
	runPostgresArchiveTool(t, "pg_dump", connection, connection.Database, "--format=custom", "--file", archive)
	info, err := os.Stat(archive)
	if err != nil {
		t.Fatal(err)
	}
	if info.Size() == 0 {
		t.Fatal("pg_dump wrote an empty archive")
	}
	t.Logf("custom archive: %d bytes", info.Size())
	restoredDatabase := createPostgresTestDatabase(t, owner)
	runPostgresArchiveTool(t, "pg_restore", connection, restoredDatabase, "--single-transaction", archive)

	// Startup checks the restored schema and runtime grants without a migration.
	t.Setenv(cfg.Postgres.ConnectionStringEnv, postgresTestRuntimeDSN(connection, restoredDatabase))
	restored := pgServer(t, cfg, nil)
	requireBytes("restored delivery artifact", read(restored, deliveryPath, ""), wantArtifact)
	requireBytes("restored scoped artifact", read(restored, v3Base+"/artifacts/"+digest, "pg reader"), wantArtifact)
	requireBytes("restored assignment", read(restored, offerPath, ""), wantOffer)
	requireBytes("restored audit", read(restored, auditPath, "pg reader"), wantAudit)

	replay := v3Publish(restored, "publish", publishKey, publisher, assignment)
	pgStatus(t, replay, published.Code)
	requireBytes("idempotent publish response", replay.Body.Bytes(), published.Body.Bytes())
	pgStatus(t, v3Publish(restored, "publish", "fresh-publish-key", publisher, assignment), http.StatusConflict)
	requireBytes("audit after replay", read(restored, auditPath, "pg reader"), wantAudit)
	requireBytes("assignment after replay", read(restored, offerPath, ""), wantOffer)

	const tenantB = "pg tenant b"
	const tenantBBase = "/v3/orgs/org-b/projects/project-b"
	pgStatus(t, pgRequest(restored, "GET", auditPath, "", tenantB, nil), http.StatusForbidden)
	pgStatus(t, pgRequest(restored, "GET", v3Base+"/artifacts/"+digest, "", tenantB, nil), http.StatusForbidden)
	if len(auditEvents(read(restored, tenantBBase+"/audit", tenantB))) != 0 {
		t.Fatal("tenant B audit contains tenant A events")
	}
	pgStatus(t, pgRequest(restored, "GET", tenantBBase+"/artifacts/"+digest, "", tenantB, nil), http.StatusNotFound)
	pgStatus(t, pgRequest(restored, "GET", artifactPath+"?organization=org-b&project=project-b", "", "", nil), http.StatusNotFound)
	tenantBOffer := f3
	tenantBOffer.Host.Scope.Organization = "org-b"
	tenantBOffer.Host.Scope.Project = "project-b"
	pgStatus(t, pgRequest(restored, "GET", v2OfferPath(tenantBOffer, 3), "", "", nil), http.StatusNoContent)
	t.Log("restored signed artifact, signed assignment, audit, idempotency and tenant read isolation verified via HTTP")

	store := restored.db.(*postgresStore)
	checkRestoredRows := func(scope tenant, wantArtifacts, wantAssignments, wantEvents int) {
		t.Helper()
		tx, ctx, cancel, err := store.begin(context.Background(), scope, "reader")
		if err != nil {
			t.Fatal(err)
		}
		defer cancel()
		defer rollbackPostgres(tx)
		// Omit tenant predicates so PostgreSQL RLS alone determines which rows are visible.
		var login string
		var artifacts, assignments, auditEvents int
		err = tx.QueryRow(ctx, `SELECT current_user,
			(SELECT count(*) FROM mixer_release.artifacts),
			(SELECT count(*) FROM mixer_release.assignments),
			(SELECT count(*) FROM mixer_release.audit_events)`).Scan(&login, &artifacts, &assignments, &auditEvents)
		if err != nil {
			t.Fatal(err)
		}
		if login != "mixer_test_runtime" || artifacts != wantArtifacts || assignments != wantAssignments || auditEvents != wantEvents {
			t.Fatalf("restored scope %+v using %s: got %d artifacts, %d assignments, %d audit events", scope, login, artifacts, assignments, auditEvents)
		}
	}
	checkRestoredRows(tenant{"org-a", "project-a"}, 1, 1, 3)
	checkRestoredRows(tenant{"org-b", "project-b"}, 0, 0, 0)
	t.Log("restricted runtime SQL saw 1 artifact, 1 assignment and 3 audit events for tenant A, and zero rows for tenant B")

	nextArtifact, nextDigest := v3Upload(t, restored, f3, "after-restore", publisher)
	nextAssignment := f3.AssignmentV3(t, nextArtifact.SignedManifest.Manifest, 2, 10000)
	pgStatus(t, v3Publish(restored, "publish", "after-restore-publish", publisher, nextAssignment), http.StatusOK)
	nextDeliveryPath := "/v3/artifacts/" + nextDigest + "?organization=org-a&project=project-a"
	nextOffer := marshal(map[string]any{"signed_assignment": nextAssignment, "artifact_url": nextDeliveryPath})
	requireBytes("sequence-2 offer after restore", read(restored, offerPath, ""), nextOffer)
	requireBytes("sequence-2 delivery after restore", read(restored, nextDeliveryPath, ""), marshal(nextArtifact))
	nextEvents := auditEvents(read(restored, auditPath, "pg reader"))
	if len(nextEvents) != len(events)+3 || !slices.Equal(nextEvents[:len(events)], events) {
		t.Fatal("new release must append three events and preserve the restored audit history")
	}
	for i, action := range []string{
		"PUT " + v3Base + "/artifacts/" + nextDigest,
		"POST " + v3Base + "/releases/validate",
		"POST " + v3Base + "/channels/beta/publish",
	} {
		index := len(events) + i
		event, prior := nextEvents[index], nextEvents[index-1]
		if event.Action != action || event.ID != prior.ID+1 || event.PreviousHash != prior.Hash {
			t.Fatalf("sequence-2 audit event %d did not extend the restored chain: %+v", i, event)
		}
	}
	t.Log("fresh signed sequence-2 publication updated the offer and delivery and extended the restored audit chain")
}

func runPostgresArchiveTool(t *testing.T, tool string, conn *pgx.ConnConfig, database string, options ...string) {
	t.Helper()
	path := os.Getenv("MIXER_TEST_" + strings.ToUpper(tool))
	if !filepath.IsAbs(path) {
		t.Fatalf("%s must be supplied by the isolated runner", tool)
	}
	args := []string{"--host", conn.Host, "--port", strconv.Itoa(int(conn.Port)), "--username", conn.User, "--dbname", database, "--no-password"}
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()
	command := exec.CommandContext(ctx, path, append(args, options...)...)
	for _, entry := range os.Environ() {
		if !strings.HasPrefix(entry, "PG") {
			command.Env = append(command.Env, entry)
		}
	}
	start := time.Now()
	output, err := command.CombinedOutput()
	if err != nil {
		t.Fatalf("%s failed: %v\n%s", tool, err, output)
	}
	t.Logf("%s completed in %s", tool, time.Since(start).Round(time.Millisecond))
}
