// Independent public-API regression probe. All keys and credentials are test-only.
package reviewprobe_test

import (
	"bytes"
	"crypto/ed25519"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"runtime"
	"strings"
	"sync"
	"testing"

	"mixer/services/protocol"
	"mixer/services/release"
)

const credential = "TEST ONLY independent configuration ownership credential"
const base = "/v1/orgs/review-org/projects/review-project"

type fixture struct {
	cfg  release.Config
	key  ed25519.PrivateKey
	host protocol.Host
}

func newFixture(t *testing.T) fixture {
	t.Helper()
	key := ed25519.NewKeyFromSeed(bytes.Repeat([]byte{91}, ed25519.SeedSize))
	scope := protocol.Scope{Organization: "review-org", Project: "review-project", App: "review-app", Environment: "development", Platform: "ios"}
	host := protocol.Host{Scope: scope, Runtime: protocol.Hash([]byte("independent review runtime")), Protocol: 1, GuestABI: 1, UISchema: 1, CapabilityHashes: map[string]string{"state": protocol.Hash([]byte("independent state"))}, StateVersion: 1, MaxPayloadBytes: 4096, Limits: protocol.Limits{MemoryBytes: 4096, Fuel: 1000, StartupMilliseconds: 1000}}
	cfg := release.Config{DeveloperMode: true, Listen: "127.0.0.1:0", DataDirectory: t.TempDir(), Tokens: []release.Token{{SHA256: protocol.Hash([]byte(credential)), Role: "publisher", Organization: scope.Organization, Project: scope.Project, Actor: "review-actor"}}, Roots: []protocol.Root{{KeyID: "review-key", Scope: scope, PublicKey: key.Public().(ed25519.PublicKey), Artifact: true, Assignment: true}}, Hosts: []protocol.Host{host}}
	return fixture{cfg, key, host}
}

func newServer(t *testing.T, cfg release.Config) *release.Server {
	t.Helper()
	s, err := release.New(cfg)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		if err := s.Close(); err != nil {
			t.Error(err)
		}
	})
	return s
}

func request(t *testing.T, s http.Handler, method, path, token, operation string, value any) *httptest.ResponseRecorder {
	t.Helper()
	var raw []byte
	if value != nil {
		var err error
		raw, err = json.Marshal(value)
		if err != nil {
			t.Fatal(err)
		}
	}
	r := httptest.NewRequest(method, path, bytes.NewReader(raw))
	r.Header.Set("Content-Type", "application/json")
	r.Header.Set("Authorization", "Bearer "+token)
	r.Header.Set("Idempotency-Key", operation)
	w := httptest.NewRecorder()
	s.ServeHTTP(w, r)
	return w
}

func status(t *testing.T, label string, w *httptest.ResponseRecorder, want int) {
	t.Helper()
	t.Logf("%s: HTTP %d; expected %d; %s", label, w.Code, want, strings.TrimSpace(w.Body.String()))
	if w.Code != want {
		t.Errorf("%s: got HTTP %d, want %d", label, w.Code, want)
	}
}

func artifact(t *testing.T, f fixture, id string, key ed25519.PrivateKey, hash string) (release.Artifact, string) {
	t.Helper()
	payload := []byte("independently authored review payload " + id)
	m := protocol.Manifest{Schema: 1, Scope: f.host.Scope, ReleaseID: id, SourceCommit: strings.Repeat("c", 40), ProvenanceID: "review-build", Runtime: f.host.Runtime, Protocol: 1, GuestABI: 1, UISchema: 1, CapabilityHashes: map[string]string{"state": hash}, StateMin: 1, StateMax: 1, PayloadSHA256: protocol.Hash(payload), CompressedBytes: uint64(len(payload)), ExpandedBytes: uint64(len(payload)), Compression: "none", AssetHashes: map[string]string{}, SourceMapSHA256: protocol.Hash(nil), Limits: protocol.Limits{MemoryBytes: 512, Fuel: 100, StartupMilliseconds: 100}, KeyID: "review-key", CreatedAtUnix: 1}
	signed, err := protocol.SignManifest(m, key)
	if err != nil {
		t.Fatal(err)
	}
	digest, err := protocol.ManifestDigest(m)
	if err != nil {
		t.Fatal(err)
	}
	return release.Artifact{SignedManifest: signed, Payload: payload}, digest
}

func upload(t *testing.T, s http.Handler, f fixture, id string, key ed25519.PrivateKey, hash string) *httptest.ResponseRecorder {
	t.Helper()
	a, d := artifact(t, f, id, key, hash)
	return request(t, s, "PUT", base+"/artifacts/"+d, credential, "upload-"+id, a)
}

func TestPublicConfigTokenRoleScopeCredentialAndActorOwnership(t *testing.T) {
	t.Run("role", func(t *testing.T) {
		f := newFixture(t)
		f.cfg.Tokens[0].Role = "reader"
		s := newServer(t, f.cfg)
		status(t, "reader before mutation", upload(t, s, f, "role-before", f.key, f.host.CapabilityHashes["state"]), 403)
		f.cfg.Tokens[0].Role = "publisher"
		status(t, "reader after caller elevates role", upload(t, s, f, "role-after", f.key, f.host.CapabilityHashes["state"]), 403)
	})
	t.Run("scope", func(t *testing.T) {
		f := newFixture(t)
		s := newServer(t, f.cfg)
		f.cfg.Tokens[0].Organization = "other-org"
		status(t, "original scope remains authorized", request(t, s, "GET", base+"/audit", credential, "", nil), 200)
		status(t, "caller cannot retarget token scope", request(t, s, "GET", strings.Replace(base, "review-org", "other-org", 1)+"/audit", credential, "", nil), 403)
	})
	t.Run("credential", func(t *testing.T) {
		f := newFixture(t)
		s := newServer(t, f.cfg)
		f.cfg.Tokens[0].SHA256 = protocol.Hash([]byte("TEST ONLY substituted credential"))
		status(t, "original bearer remains authorized", request(t, s, "GET", base+"/audit", credential, "", nil), 200)
		status(t, "caller cannot install another bearer", request(t, s, "GET", base+"/audit", "TEST ONLY substituted credential", "", nil), 401)
	})
	t.Run("actor", func(t *testing.T) {
		f := newFixture(t)
		s := newServer(t, f.cfg)
		f.cfg.Tokens[0].Actor = "forged-actor"
		status(t, "upload after caller changes actor", upload(t, s, f, "actor", f.key, f.host.CapabilityHashes["state"]), 201)
		w := request(t, s, "GET", base+"/audit", credential, "", nil)
		status(t, "audit available", w, 200)
		if !strings.Contains(w.Body.String(), `"actor":"review-actor"`) || strings.Contains(w.Body.String(), `"actor":"forged-actor"`) {
			t.Errorf("audit actor changed through caller-owned token: %s", w.Body.String())
		}
	})
}

func TestPublicConfigTrustRootBytesAndSliceOwnership(t *testing.T) {
	t.Run("public-key-bytes", func(t *testing.T) {
		f := newFixture(t)
		s := newServer(t, f.cfg)
		hash := f.host.CapabilityHashes["state"]
		other := ed25519.NewKeyFromSeed(bytes.Repeat([]byte{92}, ed25519.SeedSize))
		status(t, "foreign signer before mutation", upload(t, s, f, "foreign-before", other, hash), 422)
		copy(f.cfg.Roots[0].PublicKey, other.Public().(ed25519.PublicKey))
		status(t, "foreign signer after caller replaces trusted bytes", upload(t, s, f, "foreign-after", other, hash), 422)
		status(t, "original signer remains trusted", upload(t, s, f, "original-after", f.key, hash), 201)
	})
	t.Run("root-slice-element", func(t *testing.T) {
		f := newFixture(t)
		s := newServer(t, f.cfg)
		f.cfg.Roots[0].Revoked = true
		status(t, "caller cannot revoke server-owned root", upload(t, s, f, "root-revoked", f.key, f.host.CapabilityHashes["state"]), 201)
	})
}

func TestPublicConfigHostMapAndSliceOwnership(t *testing.T) {
	t.Run("capability-map", func(t *testing.T) {
		f := newFixture(t)
		s := newServer(t, f.cfg)
		original := f.host.CapabilityHashes["state"]
		substitute := protocol.Hash([]byte("substituted schema"))
		status(t, "substituted schema before mutation", upload(t, s, f, "schema-before", f.key, substitute), 422)
		f.cfg.Hosts[0].CapabilityHashes["state"] = substitute
		status(t, "substituted schema after caller changes map", upload(t, s, f, "schema-after", f.key, substitute), 422)
		status(t, "original schema remains compatible", upload(t, s, f, "schema-original", f.key, original), 201)
	})
	t.Run("host-slice-element", func(t *testing.T) {
		f := newFixture(t)
		s := newServer(t, f.cfg)
		f.cfg.Hosts[0].StateVersion = 99
		status(t, "caller cannot replace installed state version", upload(t, s, f, "state-after", f.key, f.host.CapabilityHashes["state"]), 201)
	})
}

func TestPublicConfigV3MapAndNestedRequestGrantControl(t *testing.T) {
	f := newFixture(t)
	f.host.Protocol = 3
	f.host.GuestABI = 2
	f.host.CapabilityHashes = map[string]string{protocol.HTTPGrantID: protocol.HTTPGrantSHA256, protocol.StorageGrantID: protocol.StorageGrantSHA256}
	f.cfg.Hosts = []protocol.Host{f.host}
	s := newServer(t, f.cfg)
	payload := []byte("TEST ONLY independent v3 payload")
	m := protocol.ManifestV3{Schema: 3, Scope: f.host.Scope, ReleaseID: "review-v3", SourceCommit: strings.Repeat("d", 40), ProvenanceID: "review-build-v3", Runtime: f.host.Runtime, Protocol: 3, GuestABI: 2, UISchema: 1, CapabilityHashes: map[string]string{protocol.HTTPGrantID: protocol.HTTPGrantSHA256, protocol.StorageGrantID: protocol.StorageGrantSHA256}, CapabilityGrants: protocol.CapabilityGrants{Schema: 1, SchemaSHA256: protocol.GrantSchemaSHA256, Entries: []protocol.CapabilityGrant{
		{CapabilityID: protocol.HTTPGrantID, SchemaSHA256: protocol.HTTPGrantSHA256, Permissions: []string{"network.https"}, Origins: []string{"https://review.example"}, Methods: []string{"GET"}, Namespaces: []string{}},
		{CapabilityID: protocol.StorageGrantID, SchemaSHA256: protocol.StorageGrantSHA256, Permissions: []string{"storage.appPrivate"}, Origins: []string{}, Methods: []string{}, Namespaces: []string{"review"}},
	}}, StateMin: 1, StateMax: 1, PayloadSHA256: protocol.Hash(payload), CompressedBytes: uint64(len(payload)), ExpandedBytes: uint64(len(payload)), Compression: "none", AssetHashes: map[string]string{}, SourceMapSHA256: protocol.Hash(nil), Limits: protocol.Limits{MemoryBytes: 512, Fuel: 100, StartupMilliseconds: 100}, KeyID: "review-key", CreatedAtUnix: 1}
	signed, err := protocol.SignManifestV3(m, f.key)
	if err != nil {
		t.Fatal(err)
	}
	digest, err := protocol.ManifestDigestV3(m)
	if err != nil {
		t.Fatal(err)
	}
	path := strings.Replace(base, "/v1/", "/v3/", 1)
	delete(f.cfg.Hosts[0].CapabilityHashes, protocol.StorageGrantID)
	w := request(t, s, "PUT", path+"/artifacts/"+digest, credential, "upload-v3", release.ArtifactV3{SignedManifest: signed, Payload: payload})
	status(t, "v3 original host survives caller map deletion", w, 201)
	if w.Code != 201 {
		return
	}
	// Grants are request data, not Config fields. Mutate the caller's request DTO
	// after its serialized HTTP upload, then verify persisted signed bytes.
	m.CapabilityGrants.Entries[0].Origins[0] = "https://changed.example"
	m.CapabilityGrants.Entries[0].Methods[0] = "POST"
	m.CapabilityGrants.Entries[1].Namespaces[0] = "changed"
	status(t, "persisted request validates after DTO mutation", request(t, s, "POST", path+"/releases/validate", credential, "validate-v3", map[string]string{"artifact_sha256": digest}), 200)
	w = request(t, s, "GET", path+"/artifacts/"+digest, credential, "", nil)
	status(t, "persisted v3 available", w, 200)
	var got release.ArtifactV3
	if err := json.Unmarshal(w.Body.Bytes(), &got); err != nil {
		t.Fatal(err)
	}
	g := got.SignedManifest.Manifest.CapabilityGrants.Entries
	if len(g) != 2 || g[0].Origins[0] != "https://review.example" || g[0].Methods[0] != "GET" || g[1].Namespaces[0] != "review" {
		t.Fatalf("persisted nested grants changed: %+v", g)
	}
}

func TestPublicConfigConcurrentCallerMutationAfterConstruction(t *testing.T) {
	for _, field := range []string{"token", "root-slice", "root-key", "host-slice", "host-map"} {
		t.Run(field, func(t *testing.T) {
			f := newFixture(t)
			s := newServer(t, f.cfg)
			hash := f.host.CapabilityHashes["state"]
			firstKeyByte := f.cfg.Roots[0].PublicKey[0]
			// New has returned before the writer begins. No concurrent access to
			// constructor inputs during New is supported or tested here.
			start := make(chan struct{})
			stop := make(chan struct{})
			var wg sync.WaitGroup
			wg.Add(1)
			go func() {
				defer wg.Done()
				<-start
				for {
					select {
					case <-stop:
						return
					default:
					}
					switch field {
					case "token":
						f.cfg.Tokens[0].Role = "publisher"
					case "root-slice":
						f.cfg.Roots[0].Revoked = false
					case "root-key":
						f.cfg.Roots[0].PublicKey[0] = firstKeyByte
					case "host-slice":
						f.cfg.Hosts[0].StateVersion = 1
					case "host-map":
						f.cfg.Hosts[0].CapabilityHashes["state"] = hash
					}
					runtime.Gosched()
				}
			}()
			close(start)
			for i := 0; i < 12; i++ {
				var w *httptest.ResponseRecorder
				if field == "token" {
					w = request(t, s, "GET", base+"/audit", credential, "", nil)
				} else {
					w = upload(t, s, f, fmt.Sprintf("race-%s-%d", field, i), f.key, hash)
				}
				want := 201
				if field == "token" {
					want = 200
				}
				if w.Code != want {
					t.Errorf("post-construction caller writes changed request result: %d %s", w.Code, w.Body.String())
				}
			}
			close(stop)
			wg.Wait()
		})
	}
}
