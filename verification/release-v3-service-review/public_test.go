package servicev3review

import (
	"bytes"
	"crypto/ed25519"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"

	"mixer/services/protocol"
	"mixer/services/release"
)

// Original external consumer: no release internals, internal/testutil, copied
// owner tests or private storage methods. These deterministic keys are TEST ONLY.
const base = "/v3/orgs/review-org/projects/review-project"

type fixture struct {
	cfg                  release.Config
	hosts                map[uint64]protocol.Host
	artifact, assignment ed25519.PrivateKey
}
type item struct {
	wire     any
	digest   string
	manifest protocol.Manifest
}

func setup(t *testing.T) fixture {
	t.Helper()
	ak := ed25519.NewKeyFromSeed(bytes.Repeat([]byte{0x71}, 32))
	sk := ed25519.NewKeyFromSeed(bytes.Repeat([]byte{0x72}, 32))
	scope := protocol.Scope{Organization: "review-org", Project: "review-project", App: "review-app", Environment: "development", Platform: "ios"}
	f := fixture{artifact: ak, assignment: sk, hosts: map[uint64]protocol.Host{}}
	for version := uint64(1); version <= 3; version++ {
		abi := uint64(1)
		hashes := map[string]string{"state": protocol.Hash([]byte("review-state"))}
		if version >= 2 {
			hashes = map[string]string{protocol.HTTPGrantID: protocol.HTTPGrantSHA256}
		}
		if version == 3 {
			abi = 2
		}
		f.hosts[version] = protocol.Host{Scope: scope, Runtime: protocol.Hash([]byte(fmt.Sprintf("TEST ONLY review runtime %d", version))), Protocol: version, GuestABI: abi, UISchema: 1,
			CapabilityHashes: hashes, StateVersion: 1, MaxPayloadBytes: 4194304, Limits: protocol.Limits{MemoryBytes: 4194304, Fuel: 1000000, StartupMilliseconds: 5000}}
	}
	f.cfg = release.Config{DeveloperMode: true, Listen: "127.0.0.1:0", DataDirectory: t.TempDir(), Roots: []protocol.Root{
		{KeyID: "review-artifact", PublicKey: ak.Public().(ed25519.PublicKey), Scope: scope, Artifact: true},
		{KeyID: "review-assignment", PublicKey: sk.Public().(ed25519.PublicKey), Scope: scope, Assignment: true}}, Hosts: []protocol.Host{f.hosts[1], f.hosts[2], f.hosts[3]}}
	for _, role := range []string{"publisher", "editor", "reader"} {
		f.cfg.Tokens = append(f.cfg.Tokens, release.Token{SHA256: protocol.Hash([]byte("TEST ONLY review " + role)), Role: role, Organization: scope.Organization, Project: scope.Project, Actor: role})
	}
	return f
}
func (f fixture) item(t *testing.T, version uint64, id string) item {
	t.Helper()
	h := f.hosts[version]
	payload := []byte("TEST ONLY independent public service payload " + id)
	m := protocol.Manifest{Schema: version, Scope: h.Scope, ReleaseID: id, SourceCommit: strings.Repeat("a", 40), ProvenanceID: "independent-review", Runtime: h.Runtime, Protocol: version, GuestABI: h.GuestABI, UISchema: 1,
		CapabilityHashes: h.CapabilityHashes, StateMin: 1, StateMax: 1, PayloadSHA256: protocol.Hash(payload), CompressedBytes: uint64(len(payload)), ExpandedBytes: uint64(len(payload)), Compression: "none", AssetHashes: map[string]string{}, SourceMapSHA256: protocol.Hash(nil),
		Limits: protocol.Limits{MemoryBytes: 65536, Fuel: 1000, StartupMilliseconds: 1000}, KeyID: "review-artifact", CreatedAtUnix: 1}
	if version == 1 {
		signed, e := protocol.SignManifest(m, f.artifact)
		if e != nil {
			t.Fatal(e)
		}
		d, e := protocol.ManifestDigest(m)
		if e != nil {
			t.Fatal(e)
		}
		return item{release.Artifact{SignedManifest: signed, Payload: payload}, d, m}
	}
	raw, _ := json.Marshal(m)
	var fields map[string]json.RawMessage
	json.Unmarshal(raw, &fields)
	fields["capability_grants"], _ = json.Marshal(protocol.CapabilityGrants{Schema: 1, SchemaSHA256: protocol.GrantSchemaSHA256, Entries: []protocol.CapabilityGrant{}})
	raw, _ = json.Marshal(fields)
	if version == 2 {
		var typed protocol.ManifestV2
		if e := json.Unmarshal(raw, &typed); e != nil {
			t.Fatal(e)
		}
		signed, e := protocol.SignManifestV2(typed, f.artifact)
		if e != nil {
			t.Fatal(e)
		}
		d, _ := protocol.ManifestDigestV2(typed)
		return item{release.ArtifactV2{SignedManifest: signed, Payload: payload}, d, m}
	}
	var typed protocol.ManifestV3
	if e := json.Unmarshal(raw, &typed); e != nil {
		t.Fatal(e)
	}
	signed, e := protocol.SignManifestV3(typed, f.artifact)
	if e != nil {
		t.Fatal(e)
	}
	d, _ := protocol.ManifestDigestV3(typed)
	return item{release.ArtifactV3{SignedManifest: signed, Payload: payload}, d, m}
}
func (f fixture) assigned(t *testing.T, version uint64, a item, sequence uint64) any {
	t.Helper()
	m := a.manifest
	v := protocol.Assignment{Schema: version, Scope: m.Scope, Channel: "beta", Cohort: "sha256-v1", RolloutBasisPoints: 10000, Sequence: sequence, ReleaseID: m.ReleaseID, ArtifactSHA256: a.digest, Runtime: m.Runtime, KeyID: "review-assignment", CreatedAtUnix: 1}
	if version == 3 {
		s, e := protocol.SignAssignmentV3(protocol.AssignmentV3(v), f.assignment)
		if e != nil {
			t.Fatal(e)
		}
		return s
	}
	if version == 2 {
		s, e := protocol.SignAssignmentV2(protocol.AssignmentV2(v), f.assignment)
		if e != nil {
			t.Fatal(e)
		}
		return s
	}
	s, e := protocol.SignAssignment(v, f.assignment)
	if e != nil {
		t.Fatal(e)
	}
	return s
}
func request(s http.Handler, method, path, key, role string, raw []byte) *httptest.ResponseRecorder {
	r := httptest.NewRequest(method, path, bytes.NewReader(raw))
	r.Header.Set("Content-Type", "application/json")
	r.Header.Set("Idempotency-Key", key)
	if role != "" {
		r.Header.Set("Authorization", "Bearer TEST ONLY review "+role)
	}
	w := httptest.NewRecorder()
	s.ServeHTTP(w, r)
	return w
}
func call(t *testing.T, s http.Handler, method, path, key, role string, value any, code int) []byte {
	t.Helper()
	var raw []byte
	if value != nil {
		var e error
		raw, e = json.Marshal(value)
		if e != nil {
			t.Fatal(e)
		}
	}
	w := request(s, method, path, key, role, raw)
	if w.Code != code {
		t.Fatalf("%s %s got%d want%d: %s", method, path, w.Code, code, w.Body.String())
	}
	return append([]byte{}, w.Body.Bytes()...)
}
func state(t *testing.T, f fixture) []byte {
	t.Helper()
	raw, e := os.ReadFile(filepath.Join(f.cfg.DataDirectory, "release.json"))
	if e != nil {
		t.Fatal(e)
	}
	return raw
}
func schema(t *testing.T, f fixture) uint64 {
	t.Helper()
	var v struct {
		Schema uint64 `json:"schema"`
	}
	if e := json.Unmarshal(state(t, f), &v); e != nil {
		t.Fatal(e)
	}
	return v.Schema
}
func route(version uint64) string {
	return fmt.Sprintf("/v%d/orgs/review-org/projects/review-project", version)
}
func offer(f fixture, version uint64) string {
	h := f.hosts[version]
	return fmt.Sprintf("/v%d/updates?organization=review-org&project=review-project&app=review-app&environment=development&platform=ios&runtime=%s&channel=beta&installation=review-install", version, h.Runtime)
}
func ready(t *testing.T, s http.Handler, f fixture, version uint64, id string, sequence uint64) item {
	t.Helper()
	a := f.item(t, version, id)
	b := route(version)
	call(t, s, "PUT", b+"/artifacts/"+a.digest, id+"-upload", "publisher", a.wire, 201)
	call(t, s, "POST", b+"/releases/validate", id+"-validate", "editor", map[string]string{"artifact_sha256": a.digest}, 200)
	call(t, s, "POST", b+"/channels/beta/publish", id+"-publish", "publisher", map[string]any{"signed_assignment": f.assigned(t, version, a, sequence)}, 200)
	return a
}

func TestPublicV3NestedFailuresDoNotWriteOrUpgrade(t *testing.T) {
	f := setup(t)
	s, e := release.New(f.cfg)
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	a := f.item(t, 3, "malformed")
	valid, _ := json.Marshal(a.wire)
	initial := state(t, f)
	cases := [][]byte{
		bytes.Replace(valid, []byte(`"schema":3`), []byte(`"Schema":3`), 1),
		bytes.Replace(valid, []byte(`"schema":3`), []byte(`"schema":3,"sche\u006da":3`), 1),
		bytes.Replace(valid, []byte(`"schema":3`), []byte(`"schema":3.0`), 1),
		bytes.Replace(valid, []byte(`"permissions":[]`), []byte(`"permissions":null`), 1),
		bytes.Replace(valid, []byte(`"payload":`), []byte(`"Payload":`), 1),
		bytes.Replace(valid, []byte(`"signed_manifest":`), []byte(`"signed_manifest":null,"extra":`), 1),
		append(valid, []byte(` {}`)...),
	}
	// Empty grant entries mean the permissions substitution above may be absent;
	// add an explicit malformed nested limits object instead of accepting a no-op.
	cases[3] = bytes.Replace(valid, []byte(`"fuel":1000`), []byte(`"fuel":null`), 1)
	for i, raw := range cases {
		if bytes.Equal(raw, valid) {
			t.Fatal("invalid no-op fixture")
		}
		w := request(s, "PUT", base+"/artifacts/"+a.digest, fmt.Sprintf("shape-%d", i), "publisher", raw)
		if w.Code != 400 {
			t.Fatalf("shape%d got%d %s", i, w.Code, w.Body.String())
		}
		if !bytes.Equal(initial, state(t, f)) {
			t.Fatal("malformed input mutated state")
		}
	}
	bad := a.wire.(release.ArtifactV3)
	bad.SignedManifest.Signature = append([]byte{}, bad.SignedManifest.Signature...)
	bad.SignedManifest.Signature[0] ^= 1
	call(t, s, "PUT", base+"/artifacts/"+a.digest, "bad-signature", "publisher", bad, 422)
	call(t, s, "PUT", base+"/artifacts/"+a.digest, "reader-upload", "reader", a.wire, 403)
	if !bytes.Equal(initial, state(t, f)) || schema(t, f) != 1 {
		t.Fatal("rejected calls changed durable schema/state")
	}
	call(t, s, "PUT", base+"/artifacts/"+a.digest, "good-upload", "editor", a.wire, 201)
	call(t, s, "GET", "/v3/artifacts/"+a.digest+"?organization=review-org&project=review-project", "", "", nil, 404)
}

func TestPublicV3PreservesLegacyBytesAndMonotonicReopen(t *testing.T) {
	f := setup(t)
	s, e := release.New(f.cfg)
	if e != nil {
		t.Fatal(e)
	}
	defer func() { s.Close() }()
	legacy := map[uint64]item{}
	oldOffers := map[uint64][]byte{}
	oldArtifacts := map[uint64][]byte{}
	for v := uint64(1); v <= 2; v++ {
		a := ready(t, s, f, v, fmt.Sprintf("old-%d", v), 11)
		legacy[v] = a
		oldOffers[v] = call(t, s, "GET", offer(f, v), "", "", nil, 200)
		oldArtifacts[v] = call(t, s, "GET", fmt.Sprintf("/v%d/artifacts/%s?organization=review-org&project=review-project", v, a.digest), "", "", nil, 200)
	}
	if schema(t, f) != 2 {
		t.Fatal("legacy schema")
	}
	beforeAudit := call(t, s, "GET", route(1)+"/audit", "", "reader", nil, 200)
	a := ready(t, s, f, 3, "new-3", 1)
	if schema(t, f) != 3 {
		t.Fatal("v3 did not upgrade")
	}
	call(t, s, "POST", route(2)+"/releases/validate", "old-after-three", "editor", map[string]string{"artifact_sha256": legacy[2].digest}, 200)
	if schema(t, f) != 3 {
		t.Fatal("legacy write downgraded schema3")
	}
	call(t, s, "POST", base+"/releases/validate", "same-key", "editor", map[string]string{"artifact_sha256": a.digest}, 200)
	call(t, s, "POST", route(2)+"/releases/validate", "same-key", "editor", map[string]string{"artifact_sha256": legacy[2].digest}, 409)
	for _, v := range []uint64{1, 2} {
		if !bytes.Equal(oldOffers[v], call(t, s, "GET", offer(f, v), "", "", nil, 200)) {
			t.Fatal("old offer rewritten")
		}
		if !bytes.Equal(oldArtifacts[v], call(t, s, "GET", fmt.Sprintf("/v%d/artifacts/%s?organization=review-org&project=review-project", v, legacy[v].digest), "", "", nil, 200)) {
			t.Fatal("old artifact rewritten")
		}
	}
	var oldHistory, newHistory struct {
		Events []json.RawMessage `json:"events"`
	}
	json.Unmarshal(beforeAudit, &oldHistory)
	json.Unmarshal(call(t, s, "GET", base+"/audit", "", "reader", nil, 200), &newHistory)
	for i, ev := range oldHistory.Events {
		if !bytes.Equal(ev, newHistory.Events[i]) {
			t.Fatal("old audit entry rewritten")
		}
	}
	prior := state(t, f)
	if e := s.Close(); e != nil {
		t.Fatal(e)
	}
	s, e = release.New(f.cfg)
	if e != nil {
		t.Fatal(e)
	}
	if !bytes.Equal(prior, state(t, f)) {
		t.Fatal("reopen rewrote saved bytes")
	}
	if schema(t, f) != 3 {
		t.Fatal("reopen schema")
	}
	call(t, s, "GET", offer(f, 3), "", "", nil, 200)
	call(t, s, "POST", base+"/channels/beta/rollback", "stale-rollback", "publisher", map[string]any{"signed_assignment": f.assigned(t, 3, a, 1)}, 409)
	call(t, s, "POST", base+"/channels/beta/rollback", "new-rollback", "publisher", map[string]any{"signed_assignment": f.assigned(t, 3, a, 2)}, 200)
}

func TestPublicV3VersionRoutesAndConcurrentExactReplay(t *testing.T) {
	f := setup(t)
	s, e := release.New(f.cfg)
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	a := ready(t, s, f, 3, "replay", 1)
	for _, v := range []uint64{1, 2} {
		call(t, s, "GET", strings.Replace(offer(f, 3), "/v3/", fmt.Sprintf("/v%d/", v), 1), "", "", nil, 204)
		call(t, s, "GET", fmt.Sprintf("/v%d/artifacts/%s?organization=review-org&project=review-project", v, a.digest), "", "", nil, 404)
	}
	signed := map[string]any{"signed_assignment": f.assigned(t, 3, a, 2)}
	raw, _ := json.Marshal(signed)
	const n = 8
	var wg sync.WaitGroup
	results := make(chan *httptest.ResponseRecorder, n)
	for i := 0; i < n; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			results <- request(s, "POST", base+"/channels/beta/promote", "identical-concurrent", "publisher", raw)
		}()
	}
	wg.Wait()
	close(results)
	var response []byte
	for w := range results {
		if w.Code != 200 {
			t.Fatalf("replay got%d %s", w.Code, w.Body.String())
		}
		if response == nil {
			response = append([]byte{}, w.Body.Bytes()...)
		} else if !bytes.Equal(response, w.Body.Bytes()) {
			t.Fatal("exact idempotent body differs")
		}
	}
	call(t, s, "POST", base+"/channels/beta/promote", "different-key-same-sequence", "publisher", signed, 409)
	w := request(s, "POST", base+"/channels/beta/promote", "identical-concurrent", "publisher", append(raw, ' '))
	if w.Code != 409 {
		t.Fatal("changed exact body reused idempotency key", w.Code)
	}
	call(t, s, "GET", "/v3/artifacts/"+a.digest+"?organization=other&project=review-project", "", "", nil, 404)
}

func TestPublicV3StoredVariantClosedAndFailureAtomic(t *testing.T) {
	f := setup(t)
	a := f.item(t, 3, "stored")
	valid, _ := json.Marshal(release.Record{Version3: ptr(a.wire.(release.ArtifactV3)), Validated: true})
	var row release.Record
	if e := json.Unmarshal(valid, &row); e != nil {
		t.Fatal(e)
	}
	back, _ := json.Marshal(row)
	if !bytes.Equal(valid, back) {
		t.Fatal("v3 record roundtrip")
	}
	for _, raw := range [][]byte{bytes.Replace(valid, []byte(`"protocol":3`), []byte(`"protocol":2`), 1), bytes.Replace(valid, []byte(`"validated":true`), []byte(`"validated":true,"artifact":{}`), 1), bytes.Replace(valid, []byte(`"validated":true`), []byte(`"validated":null`), 1), bytes.Replace(valid, []byte(`"artifact_v3":`), []byte(`"artifact_v3":null,"extra":`), 1)} {
		before := row
		if e := json.Unmarshal(raw, &row); e == nil {
			t.Fatal("mixed/malformed record accepted")
		}
		left, _ := json.Marshal(before)
		right, _ := json.Marshal(row)
		if !bytes.Equal(left, right) {
			t.Fatal("failed record decoder partially mutated destination")
		}
	}
	if _, e := json.Marshal(release.Record{Version3: ptr(a.wire.(release.ArtifactV3)), Version2: &release.ArtifactV2{}}); e == nil {
		t.Fatal("mixed in-memory record encoded")
	}
	channel := release.Channel{Version3: ptr(f.assigned(t, 3, a, 1).(protocol.SignedAssignmentV3))}
	saved, _ := json.Marshal(channel)
	for _, raw := range [][]byte{bytes.Replace(saved, []byte(`"protocol":3`), []byte(`"protocol":1`), 1), bytes.Replace(saved, []byte(`"signed_assignment_v3":`), []byte(`"signed_assignment_v3":null,"extra":`), 1)} {
		if e := json.Unmarshal(raw, &channel); e == nil {
			t.Fatal("mixed channel accepted")
		}
		got, _ := json.Marshal(channel)
		if !bytes.Equal(got, saved) {
			t.Fatal("channel decoder partially mutated")
		}
	}
}
func ptr[T any](value T) *T { return &value }
