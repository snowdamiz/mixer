package release

import (
	"bytes"
	"crypto/ed25519"
	"encoding/json"
	"fmt"
	"io"
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

const v3Base = "/v3/orgs/org-a/projects/project-a"
const v3Publisher = "TEST ONLY publisher"

func v3Config(t *testing.T, f testutil.Fixture) Config {
	t.Helper()
	cfg := v2Config(t, f)
	cfg.Hosts = append(cfg.Hosts, f.Protocol3().Host)
	return cfg
}
func v3Artifact(t *testing.T, f testutil.Fixture, id string) (ArtifactV3, string) {
	t.Helper()
	payload := []byte("TEST ONLY original protocol3 service payload " + id)
	signed := f.ManifestV3(t, payload, id)
	digest, e := protocol.ManifestDigestV3(signed.Manifest)
	if e != nil {
		t.Fatal(e)
	}
	return ArtifactV3{signed, payload}, digest
}
func v3Upload(t *testing.T, s http.Handler, f testutil.Fixture, id, token string) (ArtifactV3, string) {
	t.Helper()
	a, d := v3Artifact(t, f, id)
	v2Status(t, v2Request(s, "PUT", v3Base+"/artifacts/"+d, "upload-"+id, token, a), 201)
	v2Status(t, v2Request(s, "POST", v3Base+"/releases/validate", "validate-"+id, token, map[string]string{"artifact_sha256": d}), 200)
	return a, d
}
func v3Publish(s http.Handler, kind, key, token string, a protocol.SignedAssignmentV3) *httptest.ResponseRecorder {
	return v2Request(s, "POST", v3Base+"/channels/beta/"+kind, key, token, map[string]any{"signed_assignment": a})
}
func v3Raw(s http.Handler, method, path, key string, raw []byte) *httptest.ResponseRecorder {
	r := httptest.NewRequest(method, path, bytes.NewReader(raw))
	r.Header.Set("Content-Type", "application/json")
	r.Header.Set("Authorization", "Bearer "+v3Publisher)
	r.Header.Set("Idempotency-Key", key)
	w := httptest.NewRecorder()
	s.ServeHTTP(w, r)
	return w
}
func v3State(t *testing.T, cfg Config) []byte {
	t.Helper()
	b, e := os.ReadFile(filepath.Join(cfg.DataDirectory, "release.json"))
	if e != nil {
		t.Fatal(e)
	}
	return b
}

func TestHTTPV3CoexistenceConcurrentSequenceAndMonotonicReopen(t *testing.T) {
	f := testutil.New(t)
	f2 := f.Protocol2()
	f3 := f.Protocol3()
	next := f3
	next.Host.Runtime = protocol.Hash([]byte("TEST ONLY next protocol3 runtime"))
	cfg := v3Config(t, f)
	cfg.Hosts = append(cfg.Hosts, next.Host)
	s, e := New(cfg)
	if e != nil {
		t.Fatal(e)
	}
	defer func() { s.Close() }()
	legacyPayload := []byte("TEST ONLY v1 preservation before v3")
	legacy := Artifact{f.Manifest(t, legacyPayload, "legacy-before-v3"), legacyPayload}
	d1, _ := protocol.ManifestDigest(legacy.SignedManifest.Manifest)
	v2Status(t, v2Request(s, "PUT", v1Base+"/artifacts/"+d1, "legacy-upload", v3Publisher, legacy), 201)
	v2Status(t, v2Request(s, "POST", v1Base+"/releases/validate", "legacy-validate", v3Publisher, map[string]string{"artifact_sha256": d1}), 200)
	v2Status(t, v2Request(s, "POST", v1Base+"/channels/beta/publish", "legacy-publish", v3Publisher, map[string]any{"signed_assignment": f.Assignment(t, legacy.SignedManifest.Manifest, 9, 10000)}), 200)
	old2, d2 := v2UploadValidate(t, s, f2, "old-v2-before3", v3Publisher)
	v2Status(t, v2Request(s, "POST", v2Base+"/channels/beta/publish", "old-v2-publish", v3Publisher, v2PublishBody(f2.AssignmentV2(t, old2.SignedManifest.Manifest, 7, 10000))), 200)
	priorEvents := append([]Event{}, s.db.(*store).state.Audit...)
	oldOffer1 := v2Request(s, "GET", v2OfferPath(f, 1), "", "", nil).Body.Bytes()
	oldOffer2 := v2Request(s, "GET", v2OfferPath(f2, 2), "", "", nil).Body.Bytes()
	oldWire1 := v2Request(s, "GET", "/v1/artifacts/"+d1+"?organization=org-a&project=project-a", "", "", nil).Body.Bytes()
	oldWire2 := v2Request(s, "GET", "/v2/artifacts/"+d2+"?organization=org-a&project=project-a", "", "", nil).Body.Bytes()
	a, d := v3Artifact(t, f3, "concurrent-v3")
	const count = 12
	codes := make(chan int, count)
	var wg sync.WaitGroup
	for i := 0; i < count; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			codes <- v2Request(s, "PUT", v3Base+"/artifacts/"+d, "same-upload-v3", v3Publisher, a).Code
		}()
	}
	wg.Wait()
	close(codes)
	for code := range codes {
		if code != 201 {
			t.Fatal("v3 idempotency", code)
		}
	}
	if s.db.(*store).state.Schema != 3 || len(s.db.(*store).state.Audit) != len(priorEvents)+1 {
		t.Fatal("v3 not atomic schema/idempotency")
	}
	v2Status(t, v2Request(s, "GET", v2OfferPath(f3, 3), "", "", nil), 204)
	v2Status(t, v2Request(s, "GET", "/v3/artifacts/"+d+"?organization=org-a&project=project-a", "", "", nil), 404)
	v2Status(t, v2Request(s, "POST", v3Base+"/releases/validate", "validate-v3", v3Publisher, map[string]string{"artifact_sha256": d}), 200)
	first := f3.AssignmentV3(t, a.SignedManifest.Manifest, 1, 10000)
	v2Status(t, v3Publish(s, "publish", "publish-v3", v3Publisher, first), 200)
	for _, version := range []uint64{1, 2} {
		v2Status(t, v2Request(s, "GET", v2OfferPath(f3, version), "", "", nil), 204)
		v2Status(t, v2Request(s, "GET", fmt.Sprintf("/v%d/artifacts/%s?organization=org-a&project=project-a", version, d), "", "", nil), 404)
	}
	second := f3.AssignmentV3(t, a.SignedManifest.Manifest, 2, 10000)
	codes = make(chan int, 2)
	for i := 0; i < 2; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			codes <- v3Publish(s, "promote", fmt.Sprintf("promote-v3-%d", i), v3Publisher, second).Code
		}(i)
	}
	wg.Wait()
	close(codes)
	counts := map[int]int{}
	for code := range codes {
		counts[code]++
	}
	if counts[200] != 1 || counts[409] != 1 {
		t.Fatal("sequence race", counts)
	}
	newer, _ := v3Upload(t, s, next, "new-runtime-v3", v3Publisher)
	v2Status(t, v3Publish(s, "publish", "new-runtime-publish", v3Publisher, next.AssignmentV3(t, newer.SignedManifest.Manifest, 1, 10000)), 200)
	newerSame, _ := v3Upload(t, s, f3, "new-artifact-v3", v3Publisher)
	v2Status(t, v3Publish(s, "publish", "new-artifact-publish", v3Publisher, f3.AssignmentV3(t, newerSame.SignedManifest.Manifest, 3, 10000)), 200)
	v2Status(t, v3Publish(s, "rollback", "stale-rollback-v3", v3Publisher, first), 409)
	rollback := f3.AssignmentV3(t, a.SignedManifest.Manifest, 4, 10000)
	good := v3Publish(s, "rollback", "rollback-v3", v3Publisher, rollback)
	v2Status(t, good, 200)
	_, _ = v2UploadValidate(t, s, f2, "later-v2", v3Publisher)
	v2Status(t, v2Request(s, "PUT", v1Base+"/artifacts/"+d1, "later-v1", v3Publisher, legacy), 200)
	if s.db.(*store).state.Schema != 3 {
		t.Fatal("legacy write downgraded schema3")
	}
	s.Close()
	s, e = New(cfg)
	if e != nil {
		t.Fatal(e)
	}
	retry := v3Publish(s, "rollback", "rollback-v3", v3Publisher, rollback)
	v2Status(t, retry, 200)
	if !bytes.Equal(good.Body.Bytes(), retry.Body.Bytes()) {
		t.Fatal("reopen changed idempotent bytes")
	}
	if !bytes.Equal(oldOffer1, v2Request(s, "GET", v2OfferPath(f, 1), "", "", nil).Body.Bytes()) || !bytes.Equal(oldOffer2, v2Request(s, "GET", v2OfferPath(f2, 2), "", "", nil).Body.Bytes()) || !bytes.Equal(oldWire1, v2Request(s, "GET", "/v1/artifacts/"+d1+"?organization=org-a&project=project-a", "", "", nil).Body.Bytes()) || !bytes.Equal(oldWire2, v2Request(s, "GET", "/v2/artifacts/"+d2+"?organization=org-a&project=project-a", "", "", nil).Body.Bytes()) {
		t.Fatal("v3 changed exact legacy delivery bytes")
	}
	if !reflect.DeepEqual(priorEvents, s.db.(*store).state.Audit[:len(priorEvents)]) {
		t.Fatal("v3 changed legacy audit prefix")
	}
	offer := v2Request(s, "GET", v2OfferPath(f3, 3), "", "", nil)
	v2Status(t, offer, 200)
	if !strings.Contains(offer.Body.String(), `"sequence":4`) || !strings.Contains(offer.Body.String(), `/v3/artifacts/`) {
		t.Fatal("v3 offer binding", offer.Body.String())
	}
}

func TestHTTPV3ScopeRolesCurrentAuthorityAndHostBinding(t *testing.T) {
	f := testutil.New(t)
	f3 := f.Protocol3()
	cfg := v3Config(t, f)
	s, e := New(cfg)
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	a, d := v3Artifact(t, f3, "reject-v3")
	before := v3State(t, cfg)
	for i, bad := range []struct {
		path, token string
		body        any
		status      int
	}{
		{v3Base + "/artifacts/" + d, "", a, 401}, {v3Base + "/artifacts/" + d, "TEST ONLY reader", a, 403}, {strings.Replace(v3Base, "org-a", "org-b", 1) + "/artifacts/" + d, v3Publisher, a, 403},
		{v1Base + "/artifacts/" + d, v3Publisher, a, 400}, {v2Base + "/artifacts/" + d, v3Publisher, a, 422}, {strings.Replace(v3Base, "/v3/", "/v4/", 1) + "/artifacts/" + d, v3Publisher, a, 404},
	} {
		v2Status(t, v2Request(s, "PUT", bad.path, fmt.Sprintf("scope-v3-%d", i), bad.token, bad.body), bad.status)
	}
	tamper := a
	tamper.Payload = []byte("tampered")
	v2Status(t, v2Request(s, "PUT", v3Base+"/artifacts/"+d, "tamper-v3", v3Publisher, tamper), 422)
	tamper = a
	tamper.SignedManifest.Signature = make([]byte, 64)
	v2Status(t, v2Request(s, "PUT", v3Base+"/artifacts/"+d, "signature-v3", v3Publisher, tamper), 422)
	for i, change := range []func(*protocol.ManifestV3){func(m *protocol.ManifestV3) { m.Runtime = protocol.Hash([]byte("unknown")) }, func(m *protocol.ManifestV3) {
		m.CapabilityHashes = map[string]string{}
		m.CapabilityGrants.Entries = []protocol.CapabilityGrant{}
	}, func(m *protocol.ManifestV3) { m.Scope.Organization = "org-b" }} {
		bad := a
		bad.SignedManifest.Manifest.CapabilityHashes = map[string]string{protocol.HTTPGrantID: protocol.HTTPGrantSHA256, protocol.StorageGrantID: protocol.StorageGrantSHA256}
		change(&bad.SignedManifest.Manifest)
		bad.SignedManifest, e = protocol.SignManifestV3(bad.SignedManifest.Manifest, f.ArtifactKey)
		if e != nil {
			t.Fatal(e)
		}
		digest, _ := protocol.ManifestDigestV3(bad.SignedManifest.Manifest)
		want := 422
		if i == 2 {
			want = 403
		}
		v2Status(t, v2Request(s, "PUT", v3Base+"/artifacts/"+digest, fmt.Sprintf("host-v3-%d", i), v3Publisher, bad), want)
	}
	badABI := a
	badABI.SignedManifest.Manifest.GuestABI = 1
	canonical, e := protocol.CanonicalCBOR(badABI.SignedManifest.Manifest)
	if e != nil {
		t.Fatal(e)
	}
	badABI.SignedManifest.Signature = ed25519.Sign(f.ArtifactKey, append([]byte(protocol.ArtifactDomainV3), canonical...))
	badDigest, _ := protocol.ManifestDigestV3(badABI.SignedManifest.Manifest)
	v2Status(t, v2Request(s, "PUT", v3Base+"/artifacts/"+badDigest, "signed-wrong-abi", v3Publisher, badABI), 422)
	if !bytes.Equal(before, v3State(t, cfg)) {
		t.Fatal("failed v3 request mutated store")
	}
	a, d = v3Upload(t, s, f3, "valid-v3", v3Publisher)
	assignment := f3.AssignmentV3(t, a.SignedManifest.Manifest, 1, 10000)
	v2Status(t, v3Publish(s, "publish", "editor-cannot-publish", "TEST ONLY editor", assignment), 403)
	s.cfg.Roots[1].Revoked = true
	v2Status(t, v3Publish(s, "publish", "revoked-assignment", v3Publisher, assignment), 409)
	s.cfg.Roots[1].Revoked = false
	s.cfg.Roots[0].Revoked = true
	v2Status(t, v3Publish(s, "publish", "revoked-artifact", v3Publisher, assignment), 422)
}

func TestV3HostConfigurationUsesClosedProtocolCeilings(t *testing.T) {
	f := testutil.New(t)
	good := v3Config(t, f)
	for _, change := range []func(*protocol.Host){func(h *protocol.Host) { h.GuestABI = 1 }, func(h *protocol.Host) { h.UISchema = 2 }, func(h *protocol.Host) { h.MaxPayloadBytes = protocol.MaxV3PayloadBytes + 1 }, func(h *protocol.Host) { h.Limits.MemoryBytes = protocol.MaxV3MemoryBytes + 1 }, func(h *protocol.Host) { h.Limits.Fuel = protocol.MaxV3Fuel + 1 }, func(h *protocol.Host) { h.Limits.StartupMilliseconds = protocol.MaxV3StartupMilliseconds + 1 }, func(h *protocol.Host) { h.CapabilityHashes = map[string]string{"unknown": protocol.Hash(nil)} }} {
		cfg := good
		cfg.Hosts = append([]protocol.Host{}, good.Hosts...)
		change(&cfg.Hosts[2])
		if ValidateConfig(cfg) == nil {
			t.Fatal("invalid v3 host accepted")
		}
	}
	cfg := good
	cfg.Roots = append([]protocol.Root{}, good.Roots...)
	for len(cfg.Roots) < 129 {
		root := good.Roots[0]
		root.KeyID = fmt.Sprintf("extra-%d", len(cfg.Roots))
		cfg.Roots = append(cfg.Roots, root)
	}
	if ValidateConfig(cfg) == nil {
		t.Fatal("v3 root ceiling missing")
	}
	cfg.Hosts = cfg.Hosts[:2]
	if e := ValidateConfig(cfg); e != nil {
		t.Fatal("legacy root behavior changed", e)
	}
	cfg.Hosts = good.Hosts
	cfg.Roots = cfg.Roots[:128]
	if e := ValidateConfig(cfg); e != nil {
		t.Fatal("exact v3 root maximum rejected", e)
	}
}

func TestHTTPV3ClosedEnvelopeMalformedAndWholeDocumentLimits(t *testing.T) {
	f := testutil.New(t)
	f3 := f.Protocol3()
	cfg := v3Config(t, f)
	s, e := New(cfg)
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	a, d := v3Artifact(t, f3, "shape-v3")
	valid, _ := json.Marshal(a)
	var fields map[string]json.RawMessage
	json.Unmarshal(valid, &fields)
	invalid := [][]byte{[]byte(`{}`), []byte(`null`), []byte(`[]`), append(valid, []byte(` {}`)...), []byte(`{"signed_manifest":null,"payload":""}`), []byte(`{"signed_manifest":{},"payload":[]}`), bytes.Replace(valid, []byte(`"payload":`), []byte(`"Payload":`), 1), bytes.Replace(valid, []byte(`"payload":`), []byte(`"unknown":0,"payload":`), 1), bytes.Replace(valid, []byte(`"payload":`), []byte(`"payload":"AA==","payload":`), 1), append([]byte{255}, valid...), []byte(strings.Repeat("[", 34) + "0" + strings.Repeat("]", 34))}
	for _, name := range []string{"signed_manifest", "payload"} {
		copy := map[string]json.RawMessage{}
		for k, v := range fields {
			if k != name {
				copy[k] = v
			}
		}
		raw, _ := json.Marshal(copy)
		invalid = append(invalid, raw)
	}
	for _, payload := range []string{`[]`, `"AA"`, `"AB=="`, `"AA==\n"`} {
		copy := map[string]json.RawMessage{"signed_manifest": fields["signed_manifest"], "payload": []byte(payload)}
		raw, _ := json.Marshal(copy)
		invalid = append(invalid, raw)
	}
	oversizedSigned := append([]byte{}, fields["signed_manifest"]...)
	oversizedSigned = append(oversizedSigned[:len(oversizedSigned)-1], append(bytes.Repeat([]byte(" "), 65537-len(oversizedSigned)), byte('}'))...)
	raw := append([]byte(`{"signed_manifest":`), oversizedSigned...)
	raw = append(raw, []byte(`,"payload":`)...)
	raw = append(raw, fields["payload"]...)
	raw = append(raw, '}')
	invalid = append(invalid, raw)
	before := v3State(t, cfg)
	for i, raw := range invalid {
		v2Status(t, v3Raw(s, "PUT", v3Base+"/artifacts/"+d, fmt.Sprintf("bad-v3-%d", i), raw), 400)
	}
	if !bytes.Equal(before, v3State(t, cfg)) {
		t.Fatal("malformed envelope mutated state")
	}
	v2Status(t, v3Raw(s, "PUT", v3Base+"/artifacts/"+d, "too-big-v3", bytes.Repeat([]byte(" "), maxV3ArtifactBody+1)), 413)
	exact := append(append([]byte{}, valid...), bytes.Repeat([]byte(" "), maxV3ArtifactBody-len(valid))...)
	v2Status(t, v3Raw(s, "PUT", v3Base+"/artifacts/"+d, "exact-envelope", exact), 201)
	mutation, _ := json.Marshal(map[string]string{"artifact_sha256": d})
	exact = append(append([]byte{}, mutation...), bytes.Repeat([]byte(" "), maxV3MutationBody-len(mutation))...)
	v2Status(t, v3Raw(s, "POST", v3Base+"/releases/validate", "exact-mutation", exact), 200)
	v2Status(t, v3Raw(s, "POST", v3Base+"/releases/validate", "oversize-mutation", append(exact, ' ')), 413)
	for i, raw := range [][]byte{[]byte(`{}`), []byte(`{"artifact_sha256":null}`), []byte(`{"artifact_sha256":"a","x":1}`), []byte(`{"artifact_sha256":"a","artifact_sha256":"b"}`)} {
		v2Status(t, v3Raw(s, "POST", v3Base+"/releases/validate", fmt.Sprintf("bad-mutation-%d", i), raw), 400)
	}
	assignment := f3.AssignmentV3(t, a.SignedManifest.Manifest, 1, 10000)
	signed, _ := json.Marshal(assignment)
	oversizedSigned = append(append([]byte{}, signed[:len(signed)-1]...), append(bytes.Repeat([]byte(" "), 65537-len(signed)), byte('}'))...)
	raw = append([]byte(`{"signed_assignment":`), oversizedSigned...)
	raw = append(raw, '}')
	v2Status(t, v3Raw(s, "POST", v3Base+"/channels/beta/publish", "signed-too-large", raw), 400)
	for i, raw := range [][]byte{[]byte(`{}`), []byte(`{"signed_assignment":null}`), []byte(`{"signed_assignment":{},"extra":1}`)} {
		v2Status(t, v3Raw(s, "POST", v3Base+"/channels/beta/publish", fmt.Sprintf("bad-assignment-%d", i), raw), 400)
	}
	r := httptest.NewRequest("PUT", v3Base+"/artifacts/"+d, nil)
	r.Body = io.NopCloser(v3ReadError{})
	r.Header.Set("Content-Type", "application/json")
	r.Header.Set("Authorization", "Bearer "+v3Publisher)
	r.Header.Set("Idempotency-Key", "read-error")
	w := httptest.NewRecorder()
	s.ServeHTTP(w, r)
	v2Status(t, w, 400)
}

type v3ReadError struct{}

func (v3ReadError) Read([]byte) (int, error) { return 0, syscall.EIO }

func TestHTTPV3LocalUpgradeFaultsReopenAndRetry(t *testing.T) {
	for _, point := range []string{"before_write", "before_file_sync", "before_rename", "after_rename", "after_directory_sync"} {
		t.Run(point, func(t *testing.T) {
			f := testutil.New(t)
			f3 := f.Protocol3()
			cfg := v3Config(t, f)
			armed := false
			s, e := NewWithFault(cfg, func(where string) error {
				if armed && where == point {
					armed = false
					return syscall.ENOSPC
				}
				return nil
			})
			if e != nil {
				t.Fatal(e)
			}
			a, d := v3Artifact(t, f3, "uncertain-v3")
			armed = true
			v2Status(t, v2Request(s, "PUT", v3Base+"/artifacts/"+d, "uncertain-v3", v3Publisher, a), 503)
			v2Status(t, v2Request(s, "GET", v3Base+"/artifacts/"+d, "", "TEST ONLY reader", nil), 503)
			s.Close()
			s, e = New(cfg)
			if e != nil {
				t.Fatal(e)
			}
			defer s.Close()
			committed := point == "after_rename" || point == "after_directory_sync"
			wantSchema := uint64(1)
			if committed {
				wantSchema = 3
			}
			if s.db.(*store).state.Schema != wantSchema {
				t.Fatal("uncertain schema3 escaped atomic write")
			}
			retry := v2Request(s, "PUT", v3Base+"/artifacts/"+d, "uncertain-v3", v3Publisher, a)
			v2Status(t, retry, 201)
			if len(s.db.(*store).state.Audit) != 1 || len(s.db.(*store).state.Outbox) != 1 {
				t.Fatal("retry duplicated v3 effects")
			}
		})
	}
}

func TestV3StorageVariantsAreClosedAtomicAndRejectOlderContainers(t *testing.T) {
	f := testutil.New(t).Protocol3()
	a, d := v3Artifact(t, f, "stored-v3")
	r := Record{Version3: &a}
	c := Channel{Version3: func() *protocol.SignedAssignmentV3 {
		x := f.AssignmentV3(t, a.SignedManifest.Manifest, 1, 10000)
		return &x
	}()}
	record, _ := json.Marshal(r)
	channel, _ := json.Marshal(c)
	for _, bad := range []Record{{}, {Version3: &a, Version2: &ArtifactV2{}}, {Version3: &a, Artifact: Artifact{Payload: []byte{1}}}} {
		if _, e := json.Marshal(bad); e == nil {
			t.Fatal("mixed/absent record encoded")
		}
	}
	for _, bad := range []Channel{{}, {Version3: c.Version3, Version2: &protocol.SignedAssignmentV2{}}, {Version3: c.Version3, SignedAssignment: protocol.SignedAssignment{Signature: []byte{1}}}} {
		if _, e := json.Marshal(bad); e == nil {
			t.Fatal("mixed/absent channel encoded")
		}
	}
	for _, raw := range [][]byte{bytes.Replace(record, []byte(`"protocol":3`), []byte(`"protocol":2`), 1), bytes.Replace(record, []byte(`"artifact_v3":`), []byte(`"artifact_v2":`), 1), bytes.Replace(record, []byte(`"validated":false`), []byte(`"validated":null`), 1), bytes.Replace(record, []byte(`"published":false`), []byte(`"extra":false,"published":false`), 1)} {
		original := r
		if protocol.DecodeJSON(raw, &r) == nil || !reflect.DeepEqual(original, r) {
			t.Fatal("bad record decode was accepted or non-atomic")
		}
	}
	for _, raw := range [][]byte{bytes.Replace(channel, []byte(`"protocol":3`), []byte(`"protocol":2`), 1), bytes.Replace(channel, []byte(`"signed_assignment_v3":`), []byte(`"signed_assignment_v2":`), 1)} {
		original := c
		if protocol.DecodeJSON(raw, &c) == nil || !reflect.DeepEqual(original, c) {
			t.Fatal("bad channel decode was accepted or non-atomic")
		}
	}
	signed, _ := json.Marshal(a.SignedManifest)
	got, e := decodeStoredArtifact(signed, a.Payload)
	if e != nil || !immutableEqual(got, Record{Version3: &a}) {
		t.Fatal("explicit PG schema3 decode", e)
	}
	signed, _ = json.Marshal(c.Version3)
	gotChannel, e := decodeStoredChannel(signed)
	if e != nil || !reflect.DeepEqual(c, gotChannel) {
		t.Fatal("explicit PG assignment3 decode", e)
	}
	for _, schema := range []uint64{1, 2, 4} {
		cfg := v3Config(t, testutil.New(t))
		s, e := New(cfg)
		if e != nil {
			t.Fatal(e)
		}
		s.Close()
		state := database{Schema: schema, Artifacts: map[string]Record{artifactKey(f.Host.Scope, d): {Version3: &a}}, Channels: map[string]Channel{}, Idempotency: map[string]Dedup{}, Audit: []Event{}, Outbox: []Work{}}
		raw, _ := json.Marshal(state)
		os.WriteFile(filepath.Join(cfg.DataDirectory, "release.json"), raw, 0600)
		if reopened, e := New(cfg); e == nil {
			reopened.Close()
			t.Fatal("v3 accepted in older/unknown container", schema)
		}
	}
}

func TestHTTPV3ExactPayloadCeilingAndCorruptReopen(t *testing.T) {
	f := testutil.New(t)
	f3 := f.Protocol3()
	cfg := v3Config(t, f)
	s, e := New(cfg)
	if e != nil {
		t.Fatal(e)
	}
	payload := bytes.Repeat([]byte{0x9d}, int(protocol.MaxV3PayloadBytes))
	signed := f3.ManifestV3(t, payload, "maximum-payload-v3")
	a := ArtifactV3{signed, payload}
	digest, _ := protocol.ManifestDigestV3(signed.Manifest)
	v2Status(t, v2Request(s, "PUT", v3Base+"/artifacts/"+digest, "max-payload-v3", v3Publisher, a), 201)
	before := v3State(t, cfg)
	larger := ArtifactV3{signed, append(append([]byte{}, payload...), 1)}
	larger.SignedManifest.Manifest.ExpandedBytes++
	larger.SignedManifest.Manifest.CompressedBytes++
	larger.SignedManifest.Manifest.PayloadSHA256 = protocol.Hash(larger.Payload)
	canonical, e := protocol.CanonicalCBOR(larger.SignedManifest.Manifest)
	if e != nil {
		t.Fatal(e)
	}
	larger.SignedManifest.Signature = ed25519.Sign(f.ArtifactKey, append([]byte(protocol.ArtifactDomainV3), canonical...))
	largerDigest, _ := protocol.ManifestDigestV3(larger.SignedManifest.Manifest)
	v2Status(t, v2Request(s, "PUT", v3Base+"/artifacts/"+largerDigest, "over-payload-v3", v3Publisher, larger), 422)
	if !bytes.Equal(before, v3State(t, cfg)) {
		t.Fatal("oversize payload changed committed v3 state")
	}
	s.Close()
	var state database
	if e = protocol.DecodeJSON(before, &state); e != nil {
		t.Fatal(e)
	}
	record := state.Artifacts[artifactKey(f3.Host.Scope, digest)]
	record.Version3.Payload[0] ^= 1
	state.Artifacts[artifactKey(f3.Host.Scope, digest)] = record
	raw, e := json.Marshal(state)
	if e != nil {
		t.Fatal(e)
	}
	if e = os.WriteFile(filepath.Join(cfg.DataDirectory, "release.json"), raw, 0600); e != nil {
		t.Fatal(e)
	}
	if reopened, e := New(cfg); e == nil {
		reopened.Close()
		t.Fatal("corrupt v3 payload reopened")
	}
}
