//go:build postgres_integration

package release

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"reflect"
	"sync"
	"syscall"
	"testing"
	"time"

	"mixer/services/protocol"
)

func TestPostgresV3CoexistenceRLSReplayAndRuntimeIsolation(t *testing.T) {
	cfg, f, owner, _ := pgFixture(t)
	f2 := f.Protocol2()
	f3 := f.Protocol3()
	next := f3
	next.Host.Runtime = protocol.Hash([]byte("TEST ONLY next PostgreSQL protocol3 runtime"))
	cfg.Hosts = append(cfg.Hosts, f2.Host, f3.Host, next.Host)
	s := pgServer(t, cfg, nil)
	other := pgServer(t, cfg, nil)
	legacy, d1 := pgUpload(t, s, f, "pg-v1-before3")
	pgStatus(t, pgPublish(s, "publish", "pg-v1-before3-publish", f.Assignment(t, legacy.SignedManifest.Manifest, 9, 10000)), 200)
	old2, d2 := v2UploadValidate(t, s, f2, "pg-v2-before3", "pg publisher")
	v2Status(t, v2Request(s, "POST", v2Base+"/channels/beta/publish", "pg-v2-before3-publish", "pg publisher", v2PublishBody(f2.AssignmentV2(t, old2.SignedManifest.Manifest, 7, 10000))), 200)
	priorEvents := pgEvents(t, s)
	oldOffer1 := pgRequest(s, "GET", pgUpdates(f), "", "", nil).Body.Bytes()
	oldOffer2 := v2Request(s, "GET", v2OfferPath(f2, 2), "", "", nil).Body.Bytes()
	oldWire1 := pgRequest(s, "GET", "/v1/artifacts/"+d1+"?organization=org-a&project=project-a", "", "", nil).Body.Bytes()
	oldWire2 := pgRequest(s, "GET", "/v2/artifacts/"+d2+"?organization=org-a&project=project-a", "", "", nil).Body.Bytes()
	a, d := v3Artifact(t, f3, "pg-concurrent-v3")
	const count = 12
	codes := make(chan int, count)
	var wg sync.WaitGroup
	for i := 0; i < count; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			target := s
			if i%2 != 0 {
				target = other
			}
			codes <- v2Request(target, "PUT", v3Base+"/artifacts/"+d, "pg-v3-same-upload", "pg publisher", a).Code
		}(i)
	}
	wg.Wait()
	close(codes)
	for code := range codes {
		if code != 201 {
			t.Fatal("v3 PG concurrent idempotency", code)
		}
	}
	if len(pgEvents(t, s)) != len(priorEvents)+1 {
		t.Fatal("v3 PG duplicate upload event")
	}
	v2Status(t, v2Request(s, "PUT", v3Base+"/artifacts/"+d, "upload-pg-v1-before3", "pg publisher", a), 409)
	v2Status(t, v2Request(s, "POST", v2Base+"/releases/validate", "pg-v3-wrong-route", "pg publisher", map[string]string{"artifact_sha256": d}), 422)
	v2Status(t, v2Request(s, "POST", v3Base+"/releases/validate", "pg-v3-validate", "pg publisher", map[string]string{"artifact_sha256": d}), 200)
	v2Status(t, v3Publish(s, "publish", "pg-v3-publish", "pg editor", f3.AssignmentV3(t, a.SignedManifest.Manifest, 1, 10000)), 403)
	v2Status(t, v3Publish(s, "publish", "pg-v3-publish", "pg publisher", f3.AssignmentV3(t, a.SignedManifest.Manifest, 1, 10000)), 200)
	newer := f3.AssignmentV3(t, a.SignedManifest.Manifest, 2, 10000)
	codes = make(chan int, 2)
	for i := 0; i < 2; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			target := s
			if i == 1 {
				target = other
			}
			codes <- v3Publish(target, "promote", fmt.Sprintf("pg-v3-race-%d", i), "pg publisher", newer).Code
		}(i)
	}
	wg.Wait()
	close(codes)
	counts := map[int]int{}
	for code := range codes {
		counts[code]++
	}
	if counts[200] != 1 || counts[409] != 1 {
		t.Fatal("v3 PG sequence race", counts)
	}
	separate, _ := v3Upload(t, s, next, "pg-v3-next-runtime", "pg publisher")
	v2Status(t, v3Publish(s, "publish", "pg-v3-next-runtime-publish", "pg publisher", next.AssignmentV3(t, separate.SignedManifest.Manifest, 1, 10000)), 200)
	second, _ := v3Upload(t, s, f3, "pg-v3-second", "pg publisher")
	v2Status(t, v3Publish(s, "publish", "pg-v3-second-publish", "pg publisher", f3.AssignmentV3(t, second.SignedManifest.Manifest, 3, 10000)), 200)
	v2Status(t, v3Publish(s, "rollback", "pg-v3-stale", "pg publisher", newer), 409)
	rollback := f3.AssignmentV3(t, a.SignedManifest.Manifest, 4, 10000)
	saved := v3Publish(s, "rollback", "pg-v3-rollback", "pg publisher", rollback)
	v2Status(t, saved, 200)
	// Direct runtime SQL deliberately omits a tenant predicate: FORCE RLS must
	// still hide the published v3 row under the other tenant and deny its insert.
	store := s.db.(*postgresStore)
	tx, ctx, cancel, e := store.begin(context.Background(), tenant{"org-b", "project-b"}, "publisher")
	if e != nil {
		t.Fatal(e)
	}
	var seen int
	if e = tx.QueryRow(ctx, "SELECT count(*) FROM mixer_release.artifacts WHERE digest=$1", d).Scan(&seen); e != nil || seen != 0 {
		t.Fatal("v3 FORCE RLS leak", seen, e)
	}
	rawManifest, _ := json.Marshal(a.SignedManifest)
	if _, e = tx.Exec(ctx, "INSERT INTO mixer_release.artifacts(organization,project,digest,signed_manifest,payload) VALUES($1,$2,$3,$4,$5)", "org-a", "project-a", d, rawManifest, a.Payload); e == nil {
		t.Fatal("v3 FORCE RLS allowed cross-tenant insert")
	}
	rollbackPostgres(tx)
	cancel()
	if _, ok, e := s.db.publicArtifact(context.Background(), tenant{"org-b", "project-b"}, d); e != nil || ok {
		t.Fatal("v3 cross-tenant delivery", e)
	}
	var got []byte
	if e = owner.QueryRow(context.Background(), "SELECT signed_manifest FROM mixer_release.artifacts WHERE organization=$1 AND project=$2 AND digest=$3", "org-a", "project-a", d).Scan(&got); e != nil || !bytes.Equal(got, rawManifest) {
		t.Fatal("v3 PG signed bytes rewritten", e)
	}
	if version, e := storedSignedVersion(got, "manifest"); e != nil || version != 3 {
		t.Fatal("v3 PG dispatch", version, e)
	}
	var migration int
	var checksum string
	if e = owner.QueryRow(context.Background(), "SELECT version,checksum FROM mixer_release.schema_migrations").Scan(&migration, &checksum); e != nil || migration != 1 || checksum != "c352755698244eff1a5d65ac32d0255478ea270be1fc143a94bdbba876b47605" {
		t.Fatal("v3 changed migration", e)
	}
	other.Close()
	s.Close()
	s = pgServer(t, cfg, nil)
	retry := v3Publish(s, "rollback", "pg-v3-rollback", "pg publisher", rollback)
	v2Status(t, retry, 200)
	if !bytes.Equal(saved.Body.Bytes(), retry.Body.Bytes()) || !bytes.Equal(oldOffer1, pgRequest(s, "GET", pgUpdates(f), "", "", nil).Body.Bytes()) || !bytes.Equal(oldOffer2, v2Request(s, "GET", v2OfferPath(f2, 2), "", "", nil).Body.Bytes()) || !bytes.Equal(oldWire1, pgRequest(s, "GET", "/v1/artifacts/"+d1+"?organization=org-a&project=project-a", "", "", nil).Body.Bytes()) || !bytes.Equal(oldWire2, pgRequest(s, "GET", "/v2/artifacts/"+d2+"?organization=org-a&project=project-a", "", "", nil).Body.Bytes()) {
		t.Fatal("PG v3 reopen changed legacy/idempotent bytes")
	}
	if !reflect.DeepEqual(priorEvents, pgEvents(t, s)[:len(priorEvents)]) {
		t.Fatal("PG v3 changed old audit hashes")
	}
}

func TestPostgresV3InterruptedPublicationImmediateRestart(t *testing.T) {
	for _, point := range []string{"postgres_before_commit", "postgres_after_commit"} {
		t.Run(point, func(t *testing.T) {
			cfg, f, _, _ := pgFixture(t)
			f3 := f.Protocol3()
			cfg.Hosts = append(cfg.Hosts, f3.Host)
			armed := false
			s := pgServer(t, cfg, func(where string) error {
				if !armed || where != point {
					return nil
				}
				armed = false
				ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
				defer cancel()
				command := exec.CommandContext(ctx, os.Getenv("MIXER_TEST_PG_CTL"), "-D", os.Getenv("MIXER_TEST_POSTGRES_DATA_DIRECTORY"), "-l", os.Getenv("MIXER_TEST_POSTGRES_LOG"), "-m", "immediate", "-w", "restart")
				if output, e := command.CombinedOutput(); e != nil {
					t.Errorf("private cluster restart failed: %s", output)
					return syscall.EIO
				}
				return syscall.ENOSPC
			})
			a, _ := v3Upload(t, s, f3, "pg-v3-uncertain", "pg publisher")
			assignment := f3.AssignmentV3(t, a.SignedManifest.Manifest, 1, 10000)
			armed = true
			v2Status(t, v3Publish(s, "publish", "pg-v3-uncertain-publish", "pg publisher", assignment), 503)
			s.Close()
			s = pgServer(t, cfg, nil)
			want := 204
			if point == "postgres_after_commit" {
				want = 200
			}
			v2Status(t, v2Request(s, "GET", v2OfferPath(f3, 3), "", "", nil), want)
			v2Status(t, v3Publish(s, "publish", "pg-v3-uncertain-publish", "pg publisher", assignment), 200)
			if len(pgEvents(t, s)) != 3 {
				t.Fatal("PG v3 uncertain commit split/duplicated artifact,assignment,audit,outbox")
			}
			v2Status(t, v3Publish(s, "publish", "pg-v3-replay", "pg publisher", assignment), 409)
		})
	}
}
