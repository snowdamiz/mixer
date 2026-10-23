package release_test

import (
	"bytes"
	"context"
	"crypto/ed25519"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"testing"
	"time"

	"mixer/services/internal/testutil"
	"mixer/services/protocol"
	"mixer/services/release"
)

func config(t *testing.T, f testutil.Fixture) release.Config {
	t.Helper()
	return release.Config{DeveloperMode: true, Listen: "127.0.0.1:0", DataDirectory: t.TempDir(), Roots: f.Roots, Hosts: []protocol.Host{f.Host}, Tokens: []release.Token{{SHA256: protocol.Hash([]byte("test publisher credential")), Role: "publisher", Organization: "org-a", Project: "project-a", Actor: "test-publisher"}, {SHA256: protocol.Hash([]byte("test reader credential")), Role: "reader", Organization: "org-a", Project: "project-a", Actor: "test-reader"}, {SHA256: protocol.Hash([]byte("test editor credential")), Role: "editor", Organization: "org-a", Project: "project-a", Actor: "test-editor"}}}
}

const base = "/v1/orgs/org-a/projects/project-a"

func request(s http.Handler, method, path, key, token string, v any) *httptest.ResponseRecorder {
	var b []byte
	if v != nil {
		b, _ = json.Marshal(v)
	}
	r := httptest.NewRequest(method, path, bytes.NewReader(b))
	r.Header.Set("Content-Type", "application/json")
	if key != "" {
		r.Header.Set("Idempotency-Key", key)
	}
	if token != "" {
		r.Header.Set("Authorization", "Bearer "+token)
	}
	w := httptest.NewRecorder()
	s.ServeHTTP(w, r)
	return w
}
func status(t *testing.T, w *httptest.ResponseRecorder, want int) {
	t.Helper()
	if w.Code != want {
		t.Fatalf("status want %d got %d: %s", want, w.Code, w.Body.String())
	}
}
func upload(t *testing.T, s http.Handler, f testutil.Fixture, id string) release.Artifact {
	t.Helper()
	payload := []byte("independent guest " + id)
	m := f.Manifest(t, payload, id)
	a := release.Artifact{SignedManifest: m, Payload: payload}
	d, _ := protocol.ManifestDigest(m.Manifest)
	w := request(s, "PUT", base+"/artifacts/"+d, "upload-"+id, "test publisher credential", a)
	status(t, w, 201)
	return a
}
func validate(t *testing.T, s http.Handler, a release.Artifact, id string) {
	t.Helper()
	d, _ := protocol.ManifestDigest(a.SignedManifest.Manifest)
	status(t, request(s, "POST", base+"/releases/validate", "validate-"+id, "test publisher credential", map[string]string{"artifact_sha256": d}), 200)
}
func assignment(s protocol.SignedAssignment) any { return map[string]any{"signed_assignment": s} }
func updates(f testutil.Fixture) string {
	return "/v1/updates?organization=org-a&project=project-a&app=fieldlog&environment=development&platform=ios&runtime=" + f.Host.Runtime + "&channel=beta&installation=install-1"
}

func TestReleaseWorkflowRollbackAndRestart(t *testing.T) {
	f := testutil.New(t)
	cfg := config(t, f)
	s, e := release.New(cfg)
	if e != nil {
		t.Fatal(e)
	}
	defer func() { s.Close() }()
	status(t, request(s, "GET", updates(f), "", "", nil), 204)
	first := upload(t, s, f, "r1")
	d1, _ := protocol.ManifestDigest(first.SignedManifest.Manifest)
	status(t, request(s, "GET", "/v1/artifacts/"+d1+"?organization=org-a&project=project-a", "", "", nil), 404)
	a1 := f.Assignment(t, first.SignedManifest.Manifest, 1, 1000)
	status(t, request(s, "POST", base+"/channels/beta/publish", "pub-before-validation", "test publisher credential", assignment(a1)), 422)
	validate(t, s, first, "r1")
	w := request(s, "POST", base+"/channels/beta/publish", "publish-1", "test publisher credential", assignment(a1))
	status(t, w, 200)
	if !strings.Contains(w.Body.String(), `"delivery":"local_only"`) {
		t.Fatal("missing local-only boundary")
	}
	again := request(s, "POST", base+"/channels/beta/publish", "publish-1", "test publisher credential", assignment(a1))
	status(t, again, 200)
	if again.Body.String() != w.Body.String() {
		t.Fatal("idempotent response changed")
	}
	expanded := f.Assignment(t, first.SignedManifest.Manifest, 2, 10000)
	status(t, request(s, "POST", base+"/channels/beta/promote", "promote-2", "test publisher credential", assignment(expanded)), 200)
	w = request(s, "GET", updates(f), "", "", nil)
	status(t, w, 200)
	var update struct {
		SignedAssignment protocol.SignedAssignment `json:"signed_assignment"`
		ArtifactURL      string                    `json:"artifact_url"`
	}
	if e = protocol.DecodeJSON(w.Body.Bytes(), &update); e != nil {
		t.Fatal(e)
	}
	if update.SignedAssignment.Assignment.Sequence != 2 {
		t.Fatal("wrong assignment")
	}
	w = request(s, "GET", update.ArtifactURL, "", "", nil)
	status(t, w, 200)
	var served release.Artifact
	if e = protocol.DecodeJSON(w.Body.Bytes(), &served); e != nil {
		t.Fatal(e)
	}
	if e = protocol.VerifyManifest(served.SignedManifest, served.Payload, cfg.Roots, f.Host, uint64(time.Now().Unix())); e != nil {
		t.Fatal(e)
	}
	second := upload(t, s, f, "r2")
	validate(t, s, second, "r2")
	a3 := f.Assignment(t, second.SignedManifest.Manifest, 3, 10000)
	status(t, request(s, "POST", base+"/channels/beta/publish", "publish-3", "test publisher credential", assignment(a3)), 200)
	status(t, request(s, "POST", base+"/channels/beta/rollback", "rollback-stale", "test publisher credential", assignment(a1)), 409)
	rollback := f.Assignment(t, first.SignedManifest.Manifest, 4, 10000)
	status(t, request(s, "POST", base+"/channels/beta/rollback", "rollback-4", "test publisher credential", assignment(rollback)), 200)
	s.Close()
	s, e = release.New(cfg)
	if e != nil {
		t.Fatal(e)
	}
	status(t, request(s, "POST", base+"/channels/beta/rollback", "rollback-4", "test publisher credential", assignment(rollback)), 200)
	status(t, request(s, "POST", base+"/channels/beta/publish", "replay-after-restart", "test publisher credential", assignment(a3)), 409)
	w = request(s, "GET", updates(f), "", "", nil)
	status(t, w, 200)
	if !strings.Contains(w.Body.String(), `"sequence":4`) {
		t.Fatal("restart lost rollback")
	}
	w = request(s, "GET", base+"/audit?limit=100", "", "test reader credential", nil)
	status(t, w, 200)
	var audit struct {
		Events []release.Event `json:"events"`
		Next   uint64          `json:"next"`
	}
	if e = json.Unmarshal(w.Body.Bytes(), &audit); e != nil {
		t.Fatal(e)
	}
	if len(audit.Events) != 8 {
		t.Fatalf("expected exactly 8 successful operations, got %d", len(audit.Events))
	}
	for i, ev := range audit.Events {
		if ev.ID != uint64(i+1) || !protocol.ValidDigest(ev.Previous) || !protocol.ValidDigest(ev.Current) || !protocol.ValidDigest(ev.Hash) || ev.Actor != "test-publisher" || ev.RequestID == "" {
			t.Fatal("incomplete audit", ev)
		}
	}
	status(t, request(s, "GET", base+"/outbox?limit=2", "", "test reader credential", nil), 200)
	w = request(s, "GET", base+"/audit?after=7&limit=1", "", "test reader credential", nil)
	status(t, w, 200)
	if !strings.Contains(w.Body.String(), `"next":8`) {
		t.Fatal("cursor incorrect")
	}
}

func TestTenantRBACAndNoCredentialPublicPath(t *testing.T) {
	f := testutil.New(t)
	cfg := config(t, f)
	s, e := release.New(cfg)
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	m := f.Manifest(t, []byte("guest"), "scope")
	d, _ := protocol.ManifestDigest(m.Manifest)
	a := release.Artifact{SignedManifest: m, Payload: []byte("guest")}
	for _, token := range []string{"", "wrong"} {
		status(t, request(s, "PUT", base+"/artifacts/"+d, "scope", token, a), 401)
	}
	status(t, request(s, "PUT", base+"/artifacts/"+d, "scope", "test reader credential", a), 403)
	status(t, request(s, "PUT", "/v1/orgs/org-b/projects/project-a/artifacts/"+d, "scope", "test publisher credential", a), 403)
	status(t, request(s, "PUT", base+"/artifacts/"+d, "scope", "test editor credential", a), 201)
	status(t, request(s, "POST", base+"/channels/beta/publish", "scope-pub", "test editor credential", assignment(f.Assignment(t, m.Manifest, 1, 10000))), 403)
	status(t, request(s, "GET", base+"/audit", "", "", nil), 401)
	status(t, request(s, "GET", "/v1/orgs/org-b/projects/project-a/audit", "", "test reader credential", nil), 403)
	status(t, request(s, "GET", updates(f)+"-different", "", "", nil), 204)
	status(t, request(s, "GET", strings.Replace(updates(f), "org-a", "org-b", 1), "", "", nil), 204)
	// A token authorized in B cannot upload A's correctly signed scope into B.
	cfg.Tokens = append(cfg.Tokens, release.Token{SHA256: protocol.Hash([]byte("tenant-b credential")), Role: "publisher", Organization: "org-b", Project: "project-a", Actor: "tenant-b"})
	s.Close()
	s, e = release.New(cfg)
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	status(t, request(s, "PUT", "/v1/orgs/org-b/projects/project-a/artifacts/"+d, "cross-tenant", "tenant-b credential", a), 403)
	status(t, request(s, "GET", "/v1/orgs/org-b/projects/project-a/artifacts/"+d, "", "tenant-b credential", nil), 404)
	w := request(s, "GET", "/v1/orgs/org-b/projects/project-a/audit", "", "tenant-b credential", nil)
	status(t, w, 200)
	if strings.Contains(w.Body.String(), "test-editor") {
		t.Fatal("cross tenant audit leak")
	}
}

func TestIdempotencyConcurrencyConflictsAndImmutability(t *testing.T) {
	f := testutil.New(t)
	s, e := release.New(config(t, f))
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	m := f.Manifest(t, []byte("guest"), "concurrent")
	d, _ := protocol.ManifestDigest(m.Manifest)
	a := release.Artifact{SignedManifest: m, Payload: []byte("guest")}
	const count = 20
	var wg sync.WaitGroup
	codes := make(chan int, count)
	for i := 0; i < count; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			w := request(s, "PUT", base+"/artifacts/"+d, "same-operation", "test publisher credential", a)
			codes <- w.Code
		}()
	}
	wg.Wait()
	close(codes)
	for c := range codes {
		if c != 201 {
			t.Fatal("duplicate request response differs", c)
		}
	}
	bad := a
	bad.Payload = []byte("tampered")
	status(t, request(s, "PUT", base+"/artifacts/"+d, "same-operation", "test publisher credential", bad), 409)
	status(t, request(s, "POST", base+"/releases/validate", "same-operation", "test publisher credential", map[string]string{"artifact_sha256": d}), 409)
	status(t, request(s, "PUT", base+"/artifacts/"+d, "different-key", "test publisher credential", bad), 422)
	w := request(s, "GET", base+"/audit", "", "test reader credential", nil)
	status(t, w, 200)
	var audit struct {
		Events []release.Event `json:"events"`
	}
	json.Unmarshal(w.Body.Bytes(), &audit)
	if len(audit.Events) != 1 {
		t.Fatal("duplicate request wrote duplicate audit/outbox", len(audit.Events))
	}
	validate(t, s, a, "same")
	first := f.Assignment(t, m.Manifest, 1, 10000)
	status(t, request(s, "POST", base+"/channels/beta/publish", "initial", "test publisher credential", assignment(first)), 200)
	next := f.Assignment(t, m.Manifest, 2, 10000)
	codes = make(chan int, 2)
	for i := 0; i < 2; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			w := request(s, "POST", base+"/channels/beta/promote", "race-"+strconv.Itoa(i), "test publisher credential", assignment(next))
			codes <- w.Code
		}(i)
	}
	wg.Wait()
	close(codes)
	results := map[int]int{}
	for c := range codes {
		results[c]++
	}
	if results[200] != 1 || results[409] != 1 {
		t.Fatal("same sequence concurrent publish not fenced", results)
	}
}

func TestMalformedTamperUnknownAndRateLimits(t *testing.T) {
	f := testutil.New(t)
	s, e := release.New(config(t, f))
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	m := f.Manifest(t, []byte("guest"), "r1")
	d, _ := protocol.ManifestDigest(m.Manifest)
	a := release.Artifact{SignedManifest: m, Payload: []byte("guest")}
	a.SignedManifest.Signature = make([]byte, ed25519.SignatureSize)
	status(t, request(s, "PUT", base+"/artifacts/"+d, "bad-signature", "test publisher credential", a), 422)
	status(t, request(s, "POST", base+"/releases/validate", "", "test publisher credential", map[string]string{"artifact_sha256": d}), 400)
	for i, raw := range []string{`{"artifact_sha256":"x","artifact_sha256":"y"}`, `{"artifact_sha256":"x","delegation":{}}`, `{} {}`, `{"artifact_sha256":42}`} {
		r := httptest.NewRequest("POST", base+"/releases/validate", strings.NewReader(raw))
		r.Header.Set("Authorization", "Bearer test publisher credential")
		r.Header.Set("Idempotency-Key", fmt.Sprintf("bad-%d", i))
		r.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		s.ServeHTTP(w, r)
		status(t, w, 400)
	}
	status(t, request(s, "GET", base+"/audit?limit=101", "", "test reader credential", nil), 400)
	status(t, request(s, "GET", base+"/audit?after=bad", "", "test reader credential", nil), 400)
	status(t, request(s, "GET", "/v2/unsupported", "", "test reader credential", nil), 404)
	status(t, request(s, "GET", "/v1/updates?app=fieldlog", "", "", nil), 400)
	for i := 0; i < 120; i++ {
		w := request(s, "GET", "/healthz", "", "", nil)
		if w.Code == 429 {
			if w.Header().Get("Retry-After") != "60" {
				t.Fatal("missing retry after")
			}
			return
		}
	}
	t.Fatal("rate limit not enforced")
}

func TestDurableCommitCrashAndAuditCorruption(t *testing.T) {
	for _, point := range []string{"before_write", "before_file_sync", "before_rename", "after_rename", "after_directory_sync"} {
		t.Run(point, func(t *testing.T) {
			f := testutil.New(t)
			cfg := config(t, f)
			armed := false
			s, e := release.NewWithFault(cfg, func(p string) error {
				if armed && point == p {
					return syscall.ENOSPC
				}
				return nil
			})
			if e != nil {
				t.Fatal(e)
			}
			m := f.Manifest(t, []byte("guest"), "r1")
			d, _ := protocol.ManifestDigest(m.Manifest)
			a := release.Artifact{SignedManifest: m, Payload: []byte("guest")}
			armed = true
			status(t, request(s, "PUT", base+"/artifacts/"+d, "uncertain", "test publisher credential", a), 503)
			status(t, request(s, "GET", base+"/artifacts/"+d, "", "test reader credential", nil), 503)
			s.Close()
			s, e = release.New(cfg)
			if e != nil {
				t.Fatal(e)
			}
			defer s.Close()
			status(t, request(s, "PUT", base+"/artifacts/"+d, "uncertain", "test publisher credential", a), 201)
			w := request(s, "GET", base+"/audit", "", "test reader credential", nil)
			status(t, w, 200)
			var audit struct {
				Events []release.Event `json:"events"`
			}
			json.Unmarshal(w.Body.Bytes(), &audit)
			if len(audit.Events) != 1 {
				t.Fatal("uncertain retry duplicated committed event")
			}
			s.Close()
			path := filepath.Join(cfg.DataDirectory, "release.json")
			raw, e := os.ReadFile(path)
			if e != nil {
				t.Fatal(e)
			}
			raw = bytes.Replace(raw, []byte(`"actor":"test-publisher"`), []byte(`"actor":"intruder"`), 1)
			if e = os.WriteFile(path, raw, 0600); e != nil {
				t.Fatal(e)
			}
			if broken, e := release.New(cfg); e == nil {
				broken.Close()
				t.Fatal("tampered audit accepted")
			}
		})
	}
}

func TestConfigProductionAndRootRevocation(t *testing.T) {
	f := testutil.New(t)
	cfg := config(t, f)
	for _, bad := range []func(*release.Config){func(c *release.Config) { c.DeveloperMode = false }, func(c *release.Config) { c.Listen = "0.0.0.0:8080" }, func(c *release.Config) { c.Listen = "localhost:8080" }, func(c *release.Config) { c.Tokens = nil }, func(c *release.Config) { c.Tokens = append(c.Tokens, c.Tokens[0]) }, func(c *release.Config) { c.StorageBackend = "unknown" }, func(c *release.Config) { c.Roots = append(c.Roots, c.Roots[0]) }, func(c *release.Config) { c.Hosts = append(c.Hosts, c.Hosts[0]) }} {
		c := cfg
		bad(&c)
		if release.ValidateConfig(c) == nil {
			t.Fatal("unsafe config accepted")
		}
	}
	s, e := release.New(cfg)
	if e != nil {
		t.Fatal(e)
	}
	a := upload(t, s, f, "revoked")
	validate(t, s, a, "revoked")
	s.Close()
	cfg.Roots[0].Revoked = true
	s, e = release.New(cfg)
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	signed := f.Assignment(t, a.SignedManifest.Manifest, 1, 10000)
	status(t, request(s, "POST", base+"/channels/beta/publish", "publish-revoked", "test publisher credential", assignment(signed)), 422)
}

func TestLoopbackHTTPAndGracefulShutdown(t *testing.T) {
	f := testutil.New(t)
	cfg := config(t, f)
	listener, e := net.Listen("tcp", "127.0.0.1:0")
	if e != nil {
		t.Fatal(e)
	}
	cfg.Listen = listener.Addr().String()
	listener.Close()
	s, e := release.New(cfg)
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	done := make(chan error, 1)
	go func() { done <- s.Run(ctx) }()
	client := &http.Client{Timeout: time.Second}
	reachable := false
	for i := 0; i < 30; i++ {
		r, e := client.Get("http://" + cfg.Listen + "/healthz")
		if e == nil {
			_, _ = io.Copy(io.Discard, r.Body)
			r.Body.Close()
			if r.StatusCode == 200 {
				reachable = true
				break
			}
		}
		time.Sleep(10 * time.Millisecond)
	}
	if !reachable {
		t.Fatal("server not reachable")
	}
	cancel()
	select {
	case e := <-done:
		if e != nil && !errors.Is(e, context.Canceled) {
			t.Fatal(e)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("shutdown did not drain")
	}
}
