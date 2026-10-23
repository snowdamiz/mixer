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
	"strings"
	"sync"
	"syscall"
	"testing"
	"time"

	"mixer/services/protocol"
)

func TestPostgresV1V2CoexistenceRuntimeIsolationAndRollback(t *testing.T) {
	cfg, f, owner, _ := pgFixture(t)
	f2 := f.Protocol2()
	f3 := f2
	f3.Host.Runtime = protocol.Hash([]byte("TEST ONLY next PostgreSQL v2 runtime"))
	cfg.Hosts = append(cfg.Hosts, f2.Host, f3.Host)
	s := pgServer(t, cfg, nil)
	other := pgServer(t, cfg, nil)
	legacy, digest1 := pgUpload(t, s, f, "legacy-v1")
	pgStatus(t, pgPublish(s, "publish", "legacy-publish", f.Assignment(t, legacy.SignedManifest.Manifest, 9, 10000)), 200)
	legacyOffer := pgRequest(s, "GET", pgUpdates(f), "", "", nil).Body.Bytes()
	oldEvents := pgEvents(t, s)
	a, digest2 := v2Artifact(f2, t, "pg-v2")
	const concurrent = 12
	codes := make(chan int, concurrent)
	var wg sync.WaitGroup
	for i := 0; i < concurrent; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			target := s
			if i%2 == 1 {
				target = other
			}
			codes <- v2Request(target, "PUT", v2Base+"/artifacts/"+digest2, "same-v2-key", "pg publisher", a).Code
		}(i)
	}
	wg.Wait()
	close(codes)
	for code := range codes {
		if code != 201 {
			t.Fatal("PG v2 concurrent idempotency", code)
		}
	}
	if len(pgEvents(t, s)) != 4 {
		t.Fatal("duplicate PG v2 idempotency effect")
	}
	v2Status(t, v2Request(s, "PUT", v2Base+"/artifacts/"+digest2, "upload-legacy-v1", "pg publisher", a), 409)
	v2Status(t, v2Request(s, "POST", v1Base+"/releases/validate", "cross-version-validation", "pg publisher", map[string]string{"artifact_sha256": digest2}), 422)
	v2Status(t, v2Request(s, "POST", v2Base+"/releases/validate", "validate-v2", "pg publisher", map[string]string{"artifact_sha256": digest2}), 200)
	first := f2.AssignmentV2(t, a.SignedManifest.Manifest, 1, 10000)
	v2Status(t, v2Request(s, "POST", v2Base+"/channels/beta/publish", "publish-v2", "pg publisher", v2PublishBody(first)), 200)
	v2Status(t, v2Request(s, "GET", v2OfferPath(f2, 1), "", "", nil), 204)
	v2Status(t, v2Request(s, "GET", "/v1/artifacts/"+digest2+"?organization=org-a&project=project-a", "", "", nil), 404)
	v2Status(t, v2Request(s, "GET", "/v2/artifacts/"+digest1+"?organization=org-a&project=project-a", "", "", nil), 404)
	newer := f2.AssignmentV2(t, a.SignedManifest.Manifest, 2, 10000)
	codes = make(chan int, 2)
	for i := 0; i < 2; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			target := s
			if i == 1 {
				target = other
			}
			codes <- v2Request(target, "POST", v2Base+"/channels/beta/promote", fmt.Sprintf("v2-promote-%d", i), "pg publisher", v2PublishBody(newer)).Code
		}(i)
	}
	wg.Wait()
	close(codes)
	counts := map[int]int{}
	for code := range codes {
		counts[code]++
	}
	if counts[200] != 1 || counts[409] != 1 {
		t.Fatal("PG v2 sequence race", counts)
	}
	third, _ := v2UploadValidate(t, s, f3, "pg-new-runtime", "pg publisher")
	v2Status(t, v2Request(s, "POST", v2Base+"/channels/beta/publish", "publish-new-runtime", "pg publisher", v2PublishBody(f3.AssignmentV2(t, third.SignedManifest.Manifest, 1, 10000))), 200)
	oldRuntime := v2Request(s, "GET", v2OfferPath(f2, 2), "", "", nil)
	v2Status(t, oldRuntime, 200)
	if !strings.Contains(oldRuntime.Body.String(), `"sequence":2`) {
		t.Fatal("new PG fingerprint overwrote old runtime")
	}
	second, _ := v2UploadValidate(t, s, f2, "pg-second-v2", "pg publisher")
	v2Status(t, v2Request(s, "POST", v2Base+"/channels/beta/publish", "second-v2-publish", "pg publisher", v2PublishBody(f2.AssignmentV2(t, second.SignedManifest.Manifest, 3, 10000))), 200)
	v2Status(t, v2Request(s, "POST", v2Base+"/channels/beta/rollback", "stale-v2-rollback", "pg publisher", v2PublishBody(first)), 409)
	rollback := f2.AssignmentV2(t, a.SignedManifest.Manifest, 4, 10000)
	r := v2Request(s, "POST", v2Base+"/channels/beta/rollback", "v2-rollback", "pg publisher", v2PublishBody(rollback))
	v2Status(t, r, 200)
	other.Close()
	s.Close()
	s = pgServer(t, cfg, nil)
	retry := v2Request(s, "POST", v2Base+"/channels/beta/rollback", "v2-rollback", "pg publisher", v2PublishBody(rollback))
	v2Status(t, retry, 200)
	if !bytes.Equal(r.Body.Bytes(), retry.Body.Bytes()) || !bytes.Equal(legacyOffer, pgRequest(s, "GET", pgUpdates(f), "", "", nil).Body.Bytes()) {
		t.Fatal("PG restart changed idempotent or v1 bytes")
	}
	if !reflect.DeepEqual(oldEvents, pgEvents(t, s)[:len(oldEvents)]) {
		t.Fatal("old PG audit hashes changed")
	}
	var got []byte
	var version int
	if e := owner.QueryRow(context.Background(), "SELECT signed_manifest FROM mixer_release.artifacts WHERE organization=$1 AND project=$2 AND digest=$3", "org-a", "project-a", digest2).Scan(&got); e != nil {
		t.Fatal(e)
	}
	if version64, e := storedSignedVersion(got, "manifest"); e != nil || version64 != 2 {
		t.Fatal("PG did not preserve v2 signed bytes", e)
	}
	want, _ := json.Marshal(a.SignedManifest)
	if !bytes.Equal(got, want) {
		t.Fatal("PG rewrote signed v2 bytes")
	}
	if e := owner.QueryRow(context.Background(), "SELECT version FROM mixer_release.schema_migrations").Scan(&version); e != nil || version != 1 {
		t.Fatal("v2 unexpectedly changed SQL migration", e)
	}
	if _, ok, e := s.db.publicArtifact(context.Background(), tenant{"org-b", "project-b"}, digest2); e != nil || ok {
		t.Fatal("cross-tenant v2 delivery", e)
	}
	who := access{tenant{"org-b", "project-b"}, "publisher-b", "publisher"}
	event := Event{Organization: who.Organization, Project: who.Project, Actor: who.Actor}
	_, e := s.db.transaction(context.Background(), who, "editor", "forged-v2", protocol.Hash([]byte("forged-v2")), event, func(tx releaseTransaction) (Response, error) {
		return response(201, map[string]bool{"ok": true}), tx.saveArtifact(digest2, Record{Version2: &a})
	})
	if e == nil {
		t.Fatal("payload chose PG v2 tenant")
	}
}

func TestPostgresV2InterruptedPublicationImmediateRestart(t *testing.T) {
	for _, point := range []string{"postgres_before_commit", "postgres_after_commit"} {
		t.Run(point, func(t *testing.T) {
			cfg, f, _, _ := pgFixture(t)
			f2 := f.Protocol2()
			cfg.Hosts = append(cfg.Hosts, f2.Host)
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
					t.Errorf("private test cluster restart failed: %s", output)
					return syscall.EIO
				}
				return syscall.ENOSPC
			})
			a, _ := v2UploadValidate(t, s, f2, "pg-uncertain-v2", "pg publisher")
			assigned := f2.AssignmentV2(t, a.SignedManifest.Manifest, 1, 10000)
			armed = true
			v2Status(t, v2Request(s, "POST", v2Base+"/channels/beta/publish", "uncertain-v2-publish", "pg publisher", v2PublishBody(assigned)), 503)
			s.Close()
			s = pgServer(t, cfg, nil)
			want := 204
			if point == "postgres_after_commit" {
				want = 200
			}
			v2Status(t, v2Request(s, "GET", v2OfferPath(f2, 2), "", "", nil), want)
			v2Status(t, v2Request(s, "POST", v2Base+"/channels/beta/publish", "uncertain-v2-publish", "pg publisher", v2PublishBody(assigned)), 200)
			if len(pgEvents(t, s)) != 3 {
				t.Fatal("v2 commit/retry split assignment,audit or outbox")
			}
			v2Status(t, v2Request(s, "POST", v2Base+"/channels/beta/publish", "replay-v2", "pg publisher", v2PublishBody(assigned)), 409)
		})
	}
}
