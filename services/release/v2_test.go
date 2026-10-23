package release

import (
	"bytes"
	"crypto/ed25519"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"sync"
	"syscall"
	"testing"

	"mixer/services/internal/testutil"
	"mixer/services/protocol"
)

const v2Base = "/v2/orgs/org-a/projects/project-a"
const v1Base = "/v1/orgs/org-a/projects/project-a"

func v2Request(s http.Handler, method, path, key, token string, value any) *httptest.ResponseRecorder {
	var data []byte
	if value != nil {
		data, _ = json.Marshal(value)
	}
	r := httptest.NewRequest(method, path, bytes.NewReader(data))
	r.Header.Set("Content-Type", "application/json")
	r.Header.Set("Idempotency-Key", key)
	if token != "" {
		r.Header.Set("Authorization", "Bearer "+token)
	}
	w := httptest.NewRecorder()
	s.ServeHTTP(w, r)
	return w
}
func v2Status(t *testing.T, r *httptest.ResponseRecorder, expected int) {
	t.Helper()
	if r.Code != expected {
		t.Fatalf("HTTP%d expected%d: %s", r.Code, expected, r.Body.String())
	}
}
func v2Config(t *testing.T, f testutil.Fixture) Config {
	t.Helper()
	return Config{DeveloperMode: true, Listen: "127.0.0.1:0", DataDirectory: t.TempDir(), Hosts: []protocol.Host{f.Host, f.Protocol2().Host}, Roots: f.Roots, Tokens: []Token{
		{SHA256: protocol.Hash([]byte("TEST ONLY publisher")), Role: "publisher", Organization: "org-a", Project: "project-a", Actor: "publisher"},
		{SHA256: protocol.Hash([]byte("TEST ONLY reader")), Role: "reader", Organization: "org-a", Project: "project-a", Actor: "reader"},
		{SHA256: protocol.Hash([]byte("TEST ONLY editor")), Role: "editor", Organization: "org-a", Project: "project-a", Actor: "editor"},
	}}
}
func v2OfferPath(f testutil.Fixture, version uint64) string {
	s := f.Host.Scope
	return fmt.Sprintf("/v%d/updates?organization=%s&project=%s&app=%s&environment=%s&platform=%s&runtime=%s&channel=beta&installation=install-1", version, s.Organization, s.Project, s.App, s.Environment, s.Platform, f.Host.Runtime)
}
func v2Artifact(f testutil.Fixture, t *testing.T, id string) (ArtifactV2, string) {
	t.Helper()
	payload := []byte("TEST ONLY original HTTP signed-grants payload " + id)
	m := f.ManifestV2(t, payload, id)
	digest, _ := protocol.ManifestDigestV2(m.Manifest)
	return ArtifactV2{m, payload}, digest
}
func v2PublishBody(a protocol.SignedAssignmentV2) any {
	return map[string]any{"signed_assignment": a}
}
func v2UploadValidate(t *testing.T, s http.Handler, f testutil.Fixture, id, token string) (ArtifactV2, string) {
	t.Helper()
	a, digest := v2Artifact(f, t, id)
	v2Status(t, v2Request(s, "PUT", v2Base+"/artifacts/"+digest, "upload-"+id, token, a), 201)
	v2Status(t, v2Request(s, "POST", v2Base+"/releases/validate", "validate-"+id, token, map[string]string{"artifact_sha256": digest}), 200)
	return a, digest
}

func TestHTTPV2CoexistsWithLegacyAndPreservesRuntimeChannels(t *testing.T) {
	f := testutil.New(t)
	f2 := f.Protocol2()
	f3 := f2
	f3.Host.Runtime = protocol.Hash([]byte("TEST ONLY subsequent installed v2 fingerprint"))
	cfg := v2Config(t, f)
	cfg.Hosts = append(cfg.Hosts, f3.Host)
	s, e := New(cfg)
	if e != nil {
		t.Fatal(e)
	}
	defer func() { s.Close() }()
	const publisher = "TEST ONLY publisher"
	legacyPayload := []byte("TEST ONLY unchanged legacy HTTP payload")
	legacy := Artifact{f.Manifest(t, legacyPayload, "legacy"), legacyPayload}
	legacyDigest, _ := protocol.ManifestDigest(legacy.SignedManifest.Manifest)
	v2Status(t, v2Request(s, "PUT", v1Base+"/artifacts/"+legacyDigest, "legacy-upload", publisher, legacy), 201)
	v2Status(t, v2Request(s, "POST", v1Base+"/releases/validate", "legacy-validate", publisher, map[string]string{"artifact_sha256": legacyDigest}), 200)
	v2Status(t, v2Request(s, "POST", v1Base+"/channels/beta/publish", "legacy-publish", publisher, map[string]any{"signed_assignment": f.Assignment(t, legacy.SignedManifest.Manifest, 9, 10000)}), 200)
	legacyWire := v2Request(s, "GET", "/v1/artifacts/"+legacyDigest+"?organization=org-a&project=project-a", "", "", nil)
	legacyOffer := v2Request(s, "GET", v2OfferPath(f, 1), "", "", nil)
	oldEvents := append([]Event{}, s.db.(*store).state.Audit...)
	before, _ := os.ReadFile(filepath.Join(cfg.DataDirectory, "release.json"))
	var initial map[string]json.RawMessage
	json.Unmarshal(before, &initial)
	if string(initial["schema"]) != "1" {
		t.Fatal("legacy write upgraded schema")
	}
	a, digest := v2Artifact(f2, t, "first-v2")
	for _, bad := range []struct {
		method, path, key, token string
		body                     any
		status                   int
	}{
		{"PUT", v2Base + "/artifacts/" + digest, "unauth", "", a, 401},
		{"PUT", v2Base + "/artifacts/" + digest, "reader", "TEST ONLY reader", a, 403},
		{"PUT", "/v2/orgs/org-b/projects/project-a/artifacts/" + digest, "tenant", publisher, a, 403},
		{"PUT", v2Base + "/artifacts/" + digest, "legacy-upload", publisher, a, 409},
		{"PUT", v1Base + "/artifacts/" + digest, "wrong-v1-route", publisher, a, 400},
		{"PUT", v2Base + "/artifacts/" + legacyDigest, "wrong-v2-route", publisher, legacy, 400},
		{"PUT", strings.Replace(v2Base, "/v2/", "/v3/", 1) + "/artifacts/" + digest, "unknown-route", publisher, a, 404},
	} {
		v2Status(t, v2Request(s, bad.method, bad.path, bad.key, bad.token, bad.body), bad.status)
	}
	tampered := a
	tampered.Payload = []byte("tampered")
	v2Status(t, v2Request(s, "PUT", v2Base+"/artifacts/"+digest, "tamper", publisher, tampered), 422)
	after, _ := os.ReadFile(filepath.Join(cfg.DataDirectory, "release.json"))
	if !bytes.Equal(before, after) {
		t.Fatal("failed v2 request upgraded or mutated legacy state")
	}
	const concurrent = 12
	var wg sync.WaitGroup
	codes := make(chan int, concurrent)
	for i := 0; i < concurrent; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			codes <- v2Request(s, "PUT", v2Base+"/artifacts/"+digest, "same-v2-upload", publisher, a).Code
		}()
	}
	wg.Wait()
	close(codes)
	for code := range codes {
		if code != 201 {
			t.Fatal("concurrent v2 idempotency", code)
		}
	}
	if s.db.(*store).state.Schema != 2 || len(s.db.(*store).state.Audit) != 4 {
		t.Fatal("v2 upgrade or atomic idempotency")
	}
	v2Status(t, v2Request(s, "GET", v2OfferPath(f2, 2), "", "", nil), 204)
	v2Status(t, v2Request(s, "GET", "/v2/artifacts/"+digest+"?organization=org-a&project=project-a", "", "", nil), 404)
	v2Status(t, v2Request(s, "POST", v1Base+"/releases/validate", "wrong-version-validate", publisher, map[string]string{"artifact_sha256": digest}), 422)
	first := f2.AssignmentV2(t, a.SignedManifest.Manifest, 1, 10000)
	v2Status(t, v2Request(s, "POST", v2Base+"/channels/beta/publish", "before-validation", publisher, v2PublishBody(first)), 422)
	v2Status(t, v2Request(s, "POST", v2Base+"/releases/validate", "validate-v2", publisher, map[string]string{"artifact_sha256": digest}), 200)
	v2Status(t, v2Request(s, "POST", v2Base+"/channels/beta/publish", "editor-publish", "TEST ONLY editor", v2PublishBody(first)), 403)
	v2Status(t, v2Request(s, "POST", v2Base+"/channels/other/publish", "wrong-channel", publisher, v2PublishBody(first)), 409)
	v2Status(t, v2Request(s, "POST", v2Base+"/channels/beta/publish", "publish-v2", publisher, v2PublishBody(first)), 200)
	v2Status(t, v2Request(s, "GET", v2OfferPath(f2, 1), "", "", nil), 204)
	v2Status(t, v2Request(s, "GET", v2OfferPath(f, 2), "", "", nil), 204)
	v2Status(t, v2Request(s, "GET", "/v1/artifacts/"+digest+"?organization=org-a&project=project-a", "", "", nil), 404)
	v2Status(t, v2Request(s, "GET", v1Base+"/artifacts/"+digest, "", publisher, nil), 404)
	v2Status(t, v2Request(s, "GET", "/v2/artifacts/"+legacyDigest+"?organization=org-a&project=project-a", "", "", nil), 404)
	newer := f2.AssignmentV2(t, a.SignedManifest.Manifest, 2, 10000)
	codes = make(chan int, 2)
	for i := 0; i < 2; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			codes <- v2Request(s, "POST", v2Base+"/channels/beta/promote", fmt.Sprintf("promote-v2-%d", i), publisher, v2PublishBody(newer)).Code
		}(i)
	}
	wg.Wait()
	close(codes)
	counts := map[int]int{}
	for code := range codes {
		counts[code]++
	}
	if counts[200] != 1 || counts[409] != 1 {
		t.Fatal("v2 sequence race", counts)
	}
	third, _ := v2UploadValidate(t, s, f3, "new-fingerprint", publisher)
	v2Status(t, v2Request(s, "POST", v2Base+"/channels/beta/publish", "new-fingerprint-publish", publisher, v2PublishBody(f3.AssignmentV2(t, third.SignedManifest.Manifest, 1, 10000))), 200)
	oldOffer := v2Request(s, "GET", v2OfferPath(f2, 2), "", "", nil)
	v2Status(t, oldOffer, 200)
	if !strings.Contains(oldOffer.Body.String(), `"sequence":2`) {
		t.Fatal("new fingerprint replaced old runtime channel")
	}
	second, _ := v2UploadValidate(t, s, f2, "second-v2", publisher)
	v2Status(t, v2Request(s, "POST", v2Base+"/channels/beta/publish", "second-publish", publisher, v2PublishBody(f2.AssignmentV2(t, second.SignedManifest.Manifest, 3, 10000))), 200)
	v2Status(t, v2Request(s, "POST", v2Base+"/channels/beta/rollback", "stale-rollback", publisher, v2PublishBody(first)), 409)
	rollback := f2.AssignmentV2(t, a.SignedManifest.Manifest, 4, 10000)
	rolled := v2Request(s, "POST", v2Base+"/channels/beta/rollback", "rollback-v2", publisher, v2PublishBody(rollback))
	v2Status(t, rolled, 200)
	s.Close()
	s, e = New(cfg)
	if e != nil {
		t.Fatal(e)
	}
	retry := v2Request(s, "POST", v2Base+"/channels/beta/rollback", "rollback-v2", publisher, v2PublishBody(rollback))
	v2Status(t, retry, 200)
	if !bytes.Equal(retry.Body.Bytes(), rolled.Body.Bytes()) {
		t.Fatal("restart changed idempotent response")
	}
	if !bytes.Equal(v2Request(s, "GET", v2OfferPath(f, 1), "", "", nil).Body.Bytes(), legacyOffer.Body.Bytes()) || !bytes.Equal(v2Request(s, "GET", "/v1/artifacts/"+legacyDigest+"?organization=org-a&project=project-a", "", "", nil).Body.Bytes(), legacyWire.Body.Bytes()) {
		t.Fatal("v2 changed legacy HTTP bytes")
	}
	if !reflect.DeepEqual(oldEvents, s.db.(*store).state.Audit[:len(oldEvents)]) {
		t.Fatal("legacy audit hashes changed")
	}
	var delivered struct {
		Signed protocol.SignedAssignmentV2 `json:"signed_assignment"`
		URL    string                      `json:"artifact_url"`
	}
	offer := v2Request(s, "GET", v2OfferPath(f2, 2), "", "", nil)
	v2Status(t, offer, 200)
	if e = protocol.DecodeJSON(offer.Body.Bytes(), &delivered); e != nil || delivered.Signed.Assignment.Sequence != 4 || !strings.HasPrefix(delivered.URL, "/v2/") {
		t.Fatal("v2 delivery binding", e)
	}
	var downloaded ArtifactV2
	raw := v2Request(s, "GET", delivered.URL, "", "", nil)
	v2Status(t, raw, 200)
	if e = protocol.DecodeJSON(raw.Body.Bytes(), &downloaded); e != nil || protocol.VerifyManifestV2(downloaded.SignedManifest, downloaded.Payload, f.Roots, f2.Host, 100) != nil || protocol.VerifyAssignmentV2(delivered.Signed, downloaded.SignedManifest, f.Roots, f2.Host, "beta", "install-1", 3, 100) != nil {
		t.Fatal("HTTP v2 signed content verification", e)
	}
}

func TestHTTPV2LocalUpgradeFaultsPreserveRetryAndSchema(t *testing.T) {
	for _, point := range []string{"before_write", "before_file_sync", "before_rename", "after_rename", "after_directory_sync"} {
		t.Run(point, func(t *testing.T) {
			f := testutil.New(t)
			cfg := v2Config(t, f)
			armed := false
			s, e := NewWithFault(cfg, func(p string) error {
				if armed && p == point {
					return syscall.ENOSPC
				}
				return nil
			})
			if e != nil {
				t.Fatal(e)
			}
			a, digest := v2Artifact(f.Protocol2(), t, "upgrade-fault")
			armed = true
			v2Status(t, v2Request(s, "PUT", v2Base+"/artifacts/"+digest, "uncertain-v2", "TEST ONLY publisher", a), 503)
			v2Status(t, v2Request(s, "GET", v2Base+"/artifacts/"+digest, "", "TEST ONLY reader", nil), 503)
			s.Close()
			var state database
			raw, e := os.ReadFile(filepath.Join(cfg.DataDirectory, "release.json"))
			if e != nil {
				t.Fatal(e)
			}
			if e = protocol.DecodeJSON(raw, &state); e != nil {
				t.Fatal(e)
			}
			committed := point == "after_rename" || point == "after_directory_sync"
			if (state.Schema == 2) != committed || len(state.Audit) != map[bool]int{true: 1, false: 0}[committed] {
				t.Fatal("schema2 upgrade escaped durable transaction", state.Schema, len(state.Audit))
			}
			s, e = New(cfg)
			if e != nil {
				t.Fatal(e)
			}
			defer s.Close()
			v2Status(t, v2Request(s, "PUT", v2Base+"/artifacts/"+digest, "uncertain-v2", "TEST ONLY publisher", a), 201)
			if s.db.(*store).state.Schema != 2 || len(s.db.(*store).state.Audit) != 1 {
				t.Fatal("v2 retry duplicated or lost upgrade")
			}
		})
	}
}

func TestVersionedStoredRecordsAreClosedAtomicAndLegacyByteExact(t *testing.T) {
	f := testutil.New(t)
	payload := []byte("TEST ONLY v1 record encoding")
	legacy := Artifact{f.Manifest(t, payload, "record"), payload}
	r := Record{Artifact: legacy, Validated: true, Published: true}
	old, _ := json.Marshal(struct {
		Artifact  Artifact `json:"artifact"`
		Validated bool     `json:"validated"`
		Published bool     `json:"published"`
	}{legacy, true, true})
	got, e := json.Marshal(r)
	if e != nil || !bytes.Equal(old, got) {
		t.Fatal("v1 stored bytes changed", e)
	}
	a, _ := v2Artifact(f.Protocol2(), t, "record-v2")
	valid := Record{Version2: &a, Validated: true}
	encoded, _ := json.Marshal(valid)
	var fields map[string]json.RawMessage
	json.Unmarshal(encoded, &fields)
	for _, kind := range []string{"missing", "mixed", "unknown", "case", "missing-tag"} {
		t.Run(kind, func(t *testing.T) {
			copy := map[string]json.RawMessage{}
			for k, v := range fields {
				copy[k] = v
			}
			switch kind {
			case "missing":
				delete(copy, "artifact_v2")
			case "mixed":
				copy["artifact"] = mustV2JSON(t, legacy)
			case "unknown":
				copy["protocol"] = []byte(`3`)
			case "case":
				copy["Protocol"] = copy["protocol"]
				delete(copy, "protocol")
			case "missing-tag":
				delete(copy, "protocol")
			}
			before := mustV2JSON(t, r)
			if e := json.Unmarshal(mustV2JSON(t, copy), &r); e == nil {
				t.Fatal("ambiguous record accepted")
			}
			if !bytes.Equal(before, mustV2JSON(t, r)) {
				t.Fatal("failed record decode mutated receiver")
			}
		})
	}
	both := valid
	both.Artifact = legacy
	if _, e = json.Marshal(both); e == nil {
		t.Fatal("mixed in-memory artifact encoded")
	}
	assigned := f.Protocol2().AssignmentV2(t, a.SignedManifest.Manifest, 1, 10000)
	c := Channel{Version2: &assigned}
	channel := mustV2JSON(t, c)
	for _, bad := range []string{`{}`, strings.Replace(string(channel), `"protocol":2`, `"protocol":1`, 1), strings.Replace(string(channel), `"protocol":2`, `"protocol":2,"signed_assignment":{}`, 1)} {
		before := mustV2JSON(t, c)
		if e = json.Unmarshal([]byte(bad), &c); e == nil || !bytes.Equal(before, mustV2JSON(t, c)) {
			t.Fatal("ambiguous channel accepted/mutated")
		}
	}
}
func mustV2JSON(t *testing.T, v any) []byte {
	t.Helper()
	b, e := json.Marshal(v)
	if e != nil {
		t.Fatal(e)
	}
	return b
}

func TestLocalStoreRejectsV2VariantsInLegacySchemaAndCorruptReopen(t *testing.T) {
	for _, kind := range []string{"legacy-schema", "missing-variant", "mixed-variant", "unknown-variant", "unknown-schema"} {
		t.Run(kind, func(t *testing.T) {
			f := testutil.New(t)
			cfg := v2Config(t, f)
			s, e := New(cfg)
			if e != nil {
				t.Fatal(e)
			}
			a, digest := v2Artifact(f.Protocol2(), t, "corruption")
			v2Status(t, v2Request(s, "PUT", v2Base+"/artifacts/"+digest, "upload", "TEST ONLY publisher", a), 201)
			s.Close()
			name := filepath.Join(cfg.DataDirectory, "release.json")
			raw, _ := os.ReadFile(name)
			var fields map[string]json.RawMessage
			json.Unmarshal(raw, &fields)
			if kind == "legacy-schema" {
				fields["schema"] = []byte(`1`)
			} else if kind == "unknown-schema" {
				fields["schema"] = []byte(`3`)
			} else {
				var artifacts map[string]map[string]json.RawMessage
				json.Unmarshal(fields["artifacts"], &artifacts)
				for _, r := range artifacts {
					switch kind {
					case "missing-variant":
						delete(r, "artifact_v2")
					case "mixed-variant":
						r["artifact"] = r["artifact_v2"]
					case "unknown-variant":
						r["protocol"] = []byte(`9`)
					}
				}
				fields["artifacts"] = mustV2JSON(t, artifacts)
			}
			if e = os.WriteFile(name, mustV2JSON(t, fields), 0600); e != nil {
				t.Fatal(e)
			}
			if unexpected, e := New(cfg); e == nil {
				unexpected.Close()
				t.Fatal("corrupt discriminated snapshot reopened")
			}
		})
	}
}

func TestHTTPV2RejectsSignedInvalidGrantsVersionsAndAuthorityWithoutUpgrade(t *testing.T) {
	f := testutil.New(t)
	f2 := f.Protocol2()
	cfg := v2Config(t, f)
	s, e := New(cfg)
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	name := filepath.Join(cfg.DataDirectory, "release.json")
	before, _ := os.ReadFile(name)
	for _, change := range []struct {
		name   string
		mutate func(*protocol.ManifestV2)
	}{
		{"schema", func(m *protocol.ManifestV2) { m.Schema = 1 }},
		{"protocol", func(m *protocol.ManifestV2) { m.Protocol = 1 }},
		{"ABI", func(m *protocol.ManifestV2) { m.GuestABI = 2 }},
		{"UI", func(m *protocol.ManifestV2) { m.UISchema = 2 }},
		{"application", func(m *protocol.ManifestV2) { m.Scope.App = "other" }},
		{"environment", func(m *protocol.ManifestV2) { m.Scope.Environment = "production" }},
		{"runtime", func(m *protocol.ManifestV2) { m.Runtime = protocol.Hash([]byte("unregistered")) }},
		{"descriptor", func(m *protocol.ManifestV2) { m.CapabilityGrants.SchemaSHA256 = protocol.Hash(nil) }},
		{"grant-hash", func(m *protocol.ManifestV2) { m.CapabilityGrants.Entries[0].SchemaSHA256 = protocol.Hash(nil) }},
		{"grant-binding", func(m *protocol.ManifestV2) { delete(m.CapabilityHashes, protocol.HTTPGrantID) }},
		{"grant-origin", func(m *protocol.ManifestV2) {
			m.CapabilityGrants.Entries[0].Origins = []string{"https://*.example.test"}
		}},
		{"grant-duplicate", func(m *protocol.ManifestV2) { m.CapabilityGrants.Entries[0].Methods = []string{"GET", "GET"} }},
		{"grant-order", func(m *protocol.ManifestV2) { m.CapabilityGrants.Entries[1].Namespaces = []string{"drafts", "Drafts"} }},
	} {
		t.Run(change.name, func(t *testing.T) {
			a, _ := v2Artifact(f2, t, "invalid-"+change.name)
			change.mutate(&a.SignedManifest.Manifest)
			// TEST ONLY: deliberately sign invalid but canonical input to prove the
			// server enforces the grant/schema contract beyond signature validity.
			canonical, e := protocol.CanonicalCBOR(a.SignedManifest.Manifest)
			if e != nil {
				t.Fatal(e)
			}
			a.SignedManifest.Signature = ed25519.Sign(f.ArtifactKey, append([]byte(protocol.ArtifactDomainV2), canonical...))
			digest, _ := protocol.ManifestDigestV2(a.SignedManifest.Manifest)
			v2Status(t, v2Request(s, "PUT", v2Base+"/artifacts/"+digest, "invalid-"+change.name, "TEST ONLY publisher", a), 422)
		})
	}
	a, digest := v2Artifact(f2, t, "wrong-role-key")
	canonical, _ := protocol.CanonicalCBOR(a.SignedManifest.Manifest)
	a.SignedManifest.Signature = ed25519.Sign(f.AssignmentKey, append([]byte(protocol.ArtifactDomainV2), canonical...))
	v2Status(t, v2Request(s, "PUT", v2Base+"/artifacts/"+digest, "wrong-authority", "TEST ONLY publisher", a), 422)
	after, _ := os.ReadFile(name)
	if !bytes.Equal(before, after) {
		t.Fatal("invalid signed v2 input mutated or upgraded schema1")
	}
	wrongHost := cfg
	wrongHost.DataDirectory = t.TempDir()
	wrongHost.Hosts = append([]protocol.Host{}, cfg.Hosts...)
	wrongHost.Hosts[1].Protocol = 1
	other, e := New(wrongHost)
	if e != nil {
		t.Fatal(e)
	}
	defer other.Close()
	a, digest = v2Artifact(f2, t, "wrong-host-protocol")
	v2Status(t, v2Request(other, "PUT", v2Base+"/artifacts/"+digest, "wrong-host-protocol", "TEST ONLY publisher", a), 422)
	if other.db.(*store).state.Schema != 1 {
		t.Fatal("route/host mismatch upgraded local state")
	}
	ambiguous := cfg
	ambiguous.Hosts = append(append([]protocol.Host{}, cfg.Hosts...), cfg.Hosts[1])
	ambiguous.Hosts[2].Protocol = 1
	if ValidateConfig(ambiguous) == nil {
		t.Fatal("one scope/runtime accepted multiple protocol versions")
	}
}
