package protocol_test

import (
	"bytes"
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"math"
	"os"
	"reflect"
	"strings"
	"testing"

	"mixer/services/protocol"
)

type v3Vector struct {
	TestOnly             bool                        `json:"test_only"`
	Description          string                      `json:"description"`
	SignedManifest       protocol.SignedManifestV3   `json:"signed_manifest"`
	SignedAssignment     protocol.SignedAssignmentV3 `json:"signed_assignment"`
	Roots                []protocol.Root             `json:"roots"`
	Host                 protocol.Host               `json:"host"`
	Payload              []byte                      `json:"payload"`
	ManifestCBORHex      string                      `json:"manifest_cbor_hex"`
	AssignmentCBORHex    string                      `json:"assignment_cbor_hex"`
	ManifestMessageHex   string                      `json:"manifest_message_hex"`
	AssignmentMessageHex string                      `json:"assignment_message_hex"`
	GrantDescriptor      json.RawMessage             `json:"grant_descriptor"`
	GrantCBORHex         string                      `json:"grant_descriptor_cbor_hex"`
	ArtifactSHA256       string                      `json:"artifact_sha256"`
	Installation         string                      `json:"installation"`
	CohortBucket         uint64                      `json:"cohort_bucket"`
	VerificationTime     uint64                      `json:"verification_time_unix"`
	LastSequence         uint64                      `json:"last_sequence"`
}

func loadV3(t testing.TB) v3Vector {
	t.Helper()
	data, e := os.ReadFile("testdata/signed-release-v3.json")
	if e != nil {
		t.Fatal(e)
	}
	var v v3Vector
	if e = protocol.DecodeJSON(data, &v); e != nil {
		t.Fatal(e)
	}
	if !v.TestOnly {
		t.Fatal("test-only fixture required")
	}
	return v
}

func v3TestKey(role string) ed25519.PrivateKey {
	seed := sha256.Sum256([]byte("Mixer publicly reproducible TEST ONLY release-v3 fixture / " + role))
	return ed25519.NewKeyFromSeed(seed[:])
}

func TestV3SharedCanonicalAndSignatureVector(t *testing.T) {
	v := loadV3(t)
	for _, item := range []struct {
		value                 any
		domain, cbor, message string
		signature             []byte
		key                   []byte
	}{
		{v.SignedManifest.Manifest, protocol.ArtifactDomainV3, v.ManifestCBORHex, v.ManifestMessageHex, v.SignedManifest.Signature, v.Roots[0].PublicKey},
		{v.SignedAssignment.Assignment, protocol.AssignmentDomainV3, v.AssignmentCBORHex, v.AssignmentMessageHex, v.SignedAssignment.Signature, v.Roots[1].PublicKey},
	} {
		encoded, e := protocol.CanonicalCBOR(item.value)
		if e != nil || hex.EncodeToString(encoded) != item.cbor {
			t.Fatal("CBOR drift", e)
		}
		message := append([]byte(item.domain), encoded...)
		if hex.EncodeToString(message) != item.message || !ed25519.Verify(item.key, message, item.signature) {
			t.Fatal("signature message drift")
		}
	}
	digest, e := protocol.ManifestDigestV3(v.SignedManifest.Manifest)
	if e != nil || digest != v.ArtifactSHA256 {
		t.Fatal("artifact identity drift", e)
	}
	if e = protocol.VerifyManifestV3(v.SignedManifest, v.Payload, v.Roots, v.Host, v.VerificationTime); e != nil {
		t.Fatal(e)
	}
	if e = protocol.VerifyAssignmentV3(v.SignedAssignment, v.SignedManifest, v.Roots, v.Host, "beta", v.Installation, v.LastSequence, v.VerificationTime); e != nil {
		t.Fatal(e)
	}
	bucket, e := protocol.Cohort(protocol.Assignment(v.SignedAssignment.Assignment), v.Installation)
	if e != nil || bucket != v.CohortBucket {
		t.Fatal("cohort drift", e)
	}
	if actual := canonicalJSON(t, v.GrantDescriptor); hex.EncodeToString(actual) != v.GrantCBORHex || protocol.Hash(actual) != protocol.GrantSchemaSHA256 {
		t.Fatal("grant descriptor drift")
	}
}

func TestV3SharedRawSignedCorpus(t *testing.T) {
	v := loadV3(t)
	var corpus struct {
		TestOnly    bool   `json:"test_only"`
		Description string `json:"description"`
		Cases       []struct {
			Name     string `json:"name"`
			Accepted bool   `json:"accepted"`
			JSON     string `json:"signed_manifest_json"`
		} `json:"cases"`
		Assignments []struct {
			Name     string `json:"name"`
			Accepted bool   `json:"accepted"`
			JSON     string `json:"signed_assignment_json"`
		} `json:"assignment_cases"`
		Origins []struct {
			Value    string `json:"value"`
			Accepted bool   `json:"accepted"`
		} `json:"origin_cases"`
		Namespaces []struct {
			Value    string `json:"value"`
			Accepted bool   `json:"accepted"`
		} `json:"namespace_cases"`
	}
	data, e := os.ReadFile("testdata/release-v3-cases.json")
	if e != nil {
		t.Fatal(e)
	}
	if e = protocol.DecodeJSON(data, &corpus); e != nil {
		t.Fatal(e)
	}
	if !corpus.TestOnly || len(corpus.Cases) != 154 || len(corpus.Assignments) < 35 {
		t.Fatal("shared corpus incomplete")
	}
	for _, c := range corpus.Cases {
		t.Run("manifest/"+c.Name, func(t *testing.T) {
			s, e := protocol.DecodeSignedManifestV3([]byte(c.JSON))
			if e == nil {
				e = protocol.VerifyManifestV3(s, v.Payload, v.Roots, v.Host, v.VerificationTime)
			}
			if (e == nil) != c.Accepted {
				t.Fatalf("accepted=%v expected=%v: %v", e == nil, c.Accepted, e)
			}
		})
	}
	for _, c := range corpus.Assignments {
		t.Run("assignment/"+c.Name, func(t *testing.T) {
			s, e := protocol.DecodeSignedAssignmentV3([]byte(c.JSON))
			if e == nil {
				e = protocol.VerifyAssignmentV3(s, v.SignedManifest, v.Roots, v.Host, "beta", v.Installation, v.LastSequence, v.VerificationTime)
			}
			if (e == nil) != c.Accepted {
				t.Fatalf("accepted=%v expected=%v: %v", e == nil, c.Accepted, e)
			}
		})
	}
}

func TestV3HostAndPayloadBoundaries(t *testing.T) {
	v := loadV3(t)
	mutations := map[string]func(*protocol.Host){
		"protocol1": func(h *protocol.Host) { h.Protocol = 1 }, "protocol2": func(h *protocol.Host) { h.Protocol = 2 }, "abi1": func(h *protocol.Host) { h.GuestABI = 1 }, "ui2": func(h *protocol.Host) { h.UISchema = 2 },
		"scope": func(h *protocol.Host) { h.Scope.App = "another" }, "runtime": func(h *protocol.Host) { h.Runtime = protocol.Hash(nil) }, "state": func(h *protocol.Host) { h.StateVersion = 2 },
		"nil-map": func(h *protocol.Host) { h.CapabilityHashes = nil }, "empty-map": func(h *protocol.Host) { h.CapabilityHashes = map[string]string{} }, "unknown-map": func(h *protocol.Host) { h.CapabilityHashes = map[string]string{"unknown": protocol.Hash(nil)} },
		"zero-payload": func(h *protocol.Host) { h.MaxPayloadBytes = 0 }, "oversize-payload": func(h *protocol.Host) { h.MaxPayloadBytes = protocol.MaxV3PayloadBytes + 1 }, "narrow-payload": func(h *protocol.Host) { h.MaxPayloadBytes = 1 },
		"zero-memory": func(h *protocol.Host) { h.Limits.MemoryBytes = 0 }, "oversize-memory": func(h *protocol.Host) { h.Limits.MemoryBytes = protocol.MaxV3MemoryBytes + 1 }, "narrow-memory": func(h *protocol.Host) { h.Limits.MemoryBytes = 1 },
		"zero-fuel": func(h *protocol.Host) { h.Limits.Fuel = 0 }, "oversize-fuel": func(h *protocol.Host) { h.Limits.Fuel = protocol.MaxV3Fuel + 1 }, "narrow-fuel": func(h *protocol.Host) { h.Limits.Fuel = 1 },
		"zero-startup": func(h *protocol.Host) { h.Limits.StartupMilliseconds = 0 }, "oversize-startup": func(h *protocol.Host) { h.Limits.StartupMilliseconds = protocol.MaxV3StartupMilliseconds + 1 }, "narrow-startup": func(h *protocol.Host) { h.Limits.StartupMilliseconds = 1 },
	}
	for name, mutate := range mutations {
		t.Run(name, func(t *testing.T) {
			h := v.Host
			mutate(&h)
			if protocol.VerifyManifestV3(v.SignedManifest, v.Payload, v.Roots, h, v.VerificationTime) == nil {
				t.Fatal("invalid host accepted")
			}
		})
	}
	for _, payload := range [][]byte{nil, append(bytes.Clone(v.Payload), 0), bytes.Repeat([]byte{1}, len(v.Payload))} {
		if protocol.VerifyManifestV3(v.SignedManifest, payload, v.Roots, v.Host, v.VerificationTime) == nil {
			t.Fatal("substituted payload accepted")
		}
	}
	// Signed one-byte linear memory is valid metadata. Native integration must
	// floor it to zero pages; this test does not claim executable admission.
	m := v.SignedManifest.Manifest
	m.Limits = protocol.Limits{MemoryBytes: 1, Fuel: 1, StartupMilliseconds: 1}
	s, e := protocol.SignManifestV3(m, v3TestKey("artifact"))
	if e != nil {
		t.Fatal(e)
	}
	if e = protocol.VerifyManifestV3(s, v.Payload, v.Roots, v.Host, v.VerificationTime); e != nil {
		t.Fatal(e)
	}
	payload := make([]byte, protocol.MaxV3PayloadBytes)
	m.PayloadSHA256 = protocol.Hash(payload)
	m.CompressedBytes = uint64(len(payload))
	m.ExpandedBytes = m.CompressedBytes
	s, e = protocol.SignManifestV3(m, v3TestKey("artifact"))
	if e != nil {
		t.Fatal(e)
	}
	if e = protocol.VerifyManifestV3(s, payload, v.Roots, v.Host, v.VerificationTime); e != nil {
		t.Fatal(e)
	}
	m.CompressedBytes++
	m.ExpandedBytes++
	if _, e = protocol.SignManifestV3(m, v3TestKey("artifact")); e == nil {
		t.Fatal("payload ceiling widened")
	}
	for _, capMap := range []map[string]string{{}, {protocol.HTTPGrantID: protocol.HTTPGrantSHA256}, {protocol.StorageGrantID: protocol.StorageGrantSHA256}} {
		v := loadV3(t)
		v.Host.CapabilityHashes = capMap
		v.SignedManifest.Manifest.CapabilityHashes = capMap
		v.SignedManifest.Manifest.CapabilityGrants.Entries = []protocol.CapabilityGrant{}
		s, e := protocol.SignManifestV3(v.SignedManifest.Manifest, v3TestKey("artifact"))
		if e != nil {
			t.Fatal(e)
		}
		if e = protocol.VerifyManifestV3(s, v.Payload, v.Roots, v.Host, v.VerificationTime); e != nil {
			t.Fatal(e)
		}
	}
}

func TestV3FreshAuthorityReplayAndLegacyIsolation(t *testing.T) {
	v := loadV3(t)
	for _, mutate := range []func(*protocol.Root){func(r *protocol.Root) { r.Revoked = true }, func(r *protocol.Root) { r.NotAfterUnix = v.VerificationTime }, func(r *protocol.Root) { r.NotBeforeUnix = v.VerificationTime + 1 }, func(r *protocol.Root) { r.Artifact = false }, func(r *protocol.Root) { r.Scope.App = "other" }, func(r *protocol.Root) { r.PublicKey = make([]byte, 32) }} {
		roots := append([]protocol.Root(nil), v.Roots...)
		mutate(&roots[0])
		if protocol.VerifyAssignmentV3(v.SignedAssignment, v.SignedManifest, roots, v.Host, "beta", v.Installation, v.LastSequence, v.VerificationTime) == nil {
			t.Fatal("assignment failed to recheck artifact authority")
		}
	}
	for _, roots := range [][]protocol.Root{nil, append(append([]protocol.Root(nil), v.Roots...), v.Roots[0]), make([]protocol.Root, 129)} {
		if protocol.VerifyManifestV3(v.SignedManifest, v.Payload, roots, v.Host, v.VerificationTime) == nil {
			t.Fatal("invalid root configuration accepted")
		}
	}
	for _, last := range []uint64{7, 8, math.MaxUint64} {
		if protocol.VerifyAssignmentV3(v.SignedAssignment, v.SignedManifest, v.Roots, v.Host, "beta", v.Installation, last, v.VerificationTime) == nil {
			t.Fatal("replay accepted")
		}
	}
	a := v.SignedAssignment.Assignment
	a.Sequence = 8
	s, e := protocol.SignAssignmentV3(a, v3TestKey("assignment"))
	if e != nil {
		t.Fatal(e)
	}
	if e = protocol.VerifyAssignmentV3(s, v.SignedManifest, v.Roots, v.Host, "beta", v.Installation, 7, v.VerificationTime); e != nil {
		t.Fatal("newer assignment for same old payload rejected", e)
	}
	old := protocol.SignedManifestV2{Manifest: protocol.ManifestV2(v.SignedManifest.Manifest), Signature: v.SignedManifest.Signature}
	if protocol.VerifyManifestV2(old, v.Payload, v.Roots, v.Host, v.VerificationTime) == nil {
		t.Fatal("legacy verifier accepted v3")
	}
	legacy := loadV2(t)
	if protocol.VerifyManifestV3(protocol.SignedManifestV3{Manifest: protocol.ManifestV3(legacy.SignedManifest.Manifest), Signature: legacy.SignedManifest.Signature}, legacy.Payload, legacy.Roots, legacy.Host, legacy.VerificationTime) == nil {
		t.Fatal("v3 accepted legacy")
	}
	for _, domain := range []string{protocol.ArtifactDomain, protocol.ArtifactDomainV2, protocol.AssignmentDomainV3} {
		s := v.SignedManifest
		b, e := protocol.CanonicalCBOR(s.Manifest)
		if e != nil {
			t.Fatal(e)
		}
		s.Signature = ed25519.Sign(v3TestKey("artifact"), append([]byte(domain), b...))
		if protocol.VerifyManifestV3(s, v.Payload, v.Roots, v.Host, v.VerificationTime) == nil {
			t.Fatal("wrong signature domain accepted")
		}
	}
}

func TestV3AtomicClosedDecoding(t *testing.T) {
	v := loadV3(t)
	for _, initial := range []any{v.SignedManifest.Manifest, v.SignedManifest, v.SignedAssignment.Assignment, v.SignedAssignment} {
		kind := reflect.TypeOf(initial)
		before, e := json.Marshal(initial)
		if e != nil {
			t.Fatal(e)
		}
		for _, data := range [][]byte{[]byte(`{}`), []byte(`null`), append(append([]byte(nil), before...), []byte(`{}`)...), []byte(strings.Repeat(" ", protocol.MaxV3DocumentBytes+1))} {
			for _, decode := range []func([]byte, any) error{protocol.DecodeJSON, json.Unmarshal} {
				target := reflect.New(kind)
				target.Elem().Set(reflect.ValueOf(initial))
				if e = decode(data, target.Interface()); e == nil {
					t.Fatal("malformed document accepted", kind)
				}
				after, e := json.Marshal(target.Interface())
				if e != nil || !bytes.Equal(before, after) {
					t.Fatal("failed decoder mutated reused receiver", kind, e)
				}
			}
		}
	}
}
