package protocol_test

import (
	"bytes"
	"crypto/ed25519"
	"crypto/rand"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"math"
	"os"
	"strconv"
	"strings"
	"testing"

	"mixer/services/protocol"
)

type v2Vector struct {
	TestOnly          bool                        `json:"test_only"`
	Description       string                      `json:"description"`
	SignedManifest    protocol.SignedManifestV2   `json:"signed_manifest"`
	SignedAssignment  protocol.SignedAssignmentV2 `json:"signed_assignment"`
	Roots             []protocol.Root             `json:"roots"`
	Host              protocol.Host               `json:"host"`
	Payload           []byte                      `json:"payload"`
	ManifestCBORHex   string                      `json:"manifest_cbor_hex"`
	AssignmentCBORHex string                      `json:"assignment_cbor_hex"`
	GrantDescriptor   json.RawMessage             `json:"grant_descriptor"`
	GrantCBORHex      string                      `json:"grant_descriptor_cbor_hex"`
	ArtifactSHA256    string                      `json:"artifact_sha256"`
	Installation      string                      `json:"installation"`
	CohortBucket      uint64                      `json:"cohort_bucket"`
	VerificationTime  uint64                      `json:"verification_time_unix"`
	LastSequence      uint64                      `json:"last_sequence"`
}

func loadV2(t testing.TB) v2Vector {
	t.Helper()
	data, e := os.ReadFile("testdata/signed-release-v2.json")
	if e != nil {
		t.Fatal(e)
	}
	var v v2Vector
	if e = protocol.DecodeJSON(data, &v); e != nil {
		t.Fatal(e)
	}
	if !v.TestOnly {
		t.Fatal("fixture must be test-only")
	}
	return v
}

func TestV2StaticCrossLanguageVectorAndFrozenDescriptor(t *testing.T) {
	v := loadV2(t)
	for _, pair := range []struct {
		value    any
		expected string
	}{{v.SignedManifest.Manifest, v.ManifestCBORHex}, {v.SignedAssignment.Assignment, v.AssignmentCBORHex}} {
		b, e := protocol.CanonicalCBOR(pair.value)
		if e != nil || hex.EncodeToString(b) != pair.expected {
			t.Fatal("canonical vector changed", e)
		}
	}
	digest, e := protocol.ManifestDigestV2(v.SignedManifest.Manifest)
	if e != nil || digest != v.ArtifactSHA256 {
		t.Fatal("artifact identity changed", e)
	}
	if e = protocol.VerifyManifestV2(v.SignedManifest, v.Payload, v.Roots, v.Host, v.VerificationTime); e != nil {
		t.Fatal(e)
	}
	if e = protocol.VerifyAssignmentV2(v.SignedAssignment, v.SignedManifest, v.Roots, v.Host, "beta", v.Installation, v.LastSequence, v.VerificationTime); e != nil {
		t.Fatal(e)
	}
	bucket, e := protocol.Cohort(protocol.Assignment(v.SignedAssignment.Assignment), v.Installation)
	if e != nil || bucket != v.CohortBucket {
		t.Fatal("cohort changed", e)
	}
	var contract struct {
		Descriptor json.RawMessage `json:"capability_grant_descriptor"`
		Hash       string          `json:"capability_grant_descriptor_sha256"`
	}
	data, e := os.ReadFile("../../contracts/release-v2.json")
	if e != nil {
		t.Fatal(e)
	}
	if e = json.Unmarshal(data, &contract); e != nil {
		t.Fatal(e)
	}
	descriptor := canonicalJSON(t, contract.Descriptor)
	expected, e := hex.DecodeString(v.GrantCBORHex)
	if e != nil || !bytes.Equal(descriptor, expected) || protocol.Hash(descriptor) != protocol.GrantSchemaSHA256 || contract.Hash != protocol.GrantSchemaSHA256 {
		t.Fatal("descriptor drift", e)
	}
	if !bytes.Equal(canonicalJSON(t, v.GrantDescriptor), descriptor) {
		t.Fatal("fixture descriptor drift")
	}
}

func canonicalJSON(t testing.TB, raw []byte) []byte {
	t.Helper()
	d := json.NewDecoder(bytes.NewReader(raw))
	d.UseNumber()
	var value any
	if e := d.Decode(&value); e != nil {
		t.Fatal(e)
	}
	var convert func(any) any
	convert = func(v any) any {
		switch n := v.(type) {
		case json.Number:
			u, e := strconv.ParseUint(string(n), 10, 64)
			if e != nil {
				t.Fatal(e)
			}
			return u
		case map[string]any:
			for k, item := range n {
				n[k] = convert(item)
			}
		case []any:
			for i, item := range n {
				n[i] = convert(item)
			}
		}
		return v
	}
	b, e := protocol.CanonicalCBOR(convert(value))
	if e != nil {
		t.Fatal(e)
	}
	return b
}

type grantCorpus struct {
	TestOnly    bool   `json:"test_only"`
	Description string `json:"description"`
	Cases       []struct {
		Name     string `json:"name"`
		Accepted bool   `json:"accepted"`
		JSON     string `json:"signed_manifest_json"`
	} `json:"cases"`
	Origins []struct {
		Value    string `json:"value"`
		Accepted bool   `json:"accepted"`
	} `json:"origin_cases"`
	Namespaces []struct {
		Value    string `json:"value"`
		Accepted bool   `json:"accepted"`
	} `json:"namespace_cases"`
}

func corpusV2(t testing.TB) grantCorpus {
	t.Helper()
	b, e := os.ReadFile("testdata/capability-grant-cases-v1.json")
	if e != nil {
		t.Fatal(e)
	}
	var v grantCorpus
	if e = protocol.DecodeJSON(b, &v); e != nil {
		t.Fatal(e)
	}
	if !v.TestOnly || len(v.Cases) != 115 {
		t.Fatal("missing shared cases")
	}
	return v
}

func TestV2SharedSignedGrantCorpus(t *testing.T) {
	v := loadV2(t)
	corpus := corpusV2(t)
	for _, item := range corpus.Cases {
		t.Run(item.Name, func(t *testing.T) {
			s, e := protocol.DecodeSignedManifestV2([]byte(item.JSON))
			if e == nil {
				e = protocol.VerifyManifestV2(s, v.Payload, v.Roots, v.Host, v.VerificationTime)
			}
			if (e == nil) != item.Accepted {
				t.Fatalf("accepted=%v expected=%v: %v", e == nil, item.Accepted, e)
			}
		})
	}
	for _, item := range corpus.Origins {
		if protocol.ValidGrantOrigin(item.Value) != item.Accepted {
			t.Errorf("origin grammar drift: %q", item.Value)
		}
	}
}

func encodedV2(t testing.TB, value any) []byte {
	t.Helper()
	b, e := json.Marshal(value)
	if e != nil {
		t.Fatal(e)
	}
	return b
}
func removeRequiredFieldsV2(t *testing.T, raw []byte, decode func([]byte) error) {
	t.Helper()
	var values map[string]json.RawMessage
	if e := json.Unmarshal(raw, &values); e != nil {
		t.Fatal(e)
	}
	for key := range values {
		t.Run(key, func(t *testing.T) {
			copy := map[string]json.RawMessage{}
			for name, v := range values {
				if name != key {
					copy[name] = v
				}
			}
			if e := decode(encodedV2(t, copy)); e == nil {
				t.Fatalf("missing required %s accepted", key)
			}
		})
	}
}
func TestV2AllTransportFieldsAreRequiredAndCaseExact(t *testing.T) {
	v := loadV2(t)
	removeRequiredFieldsV2(t, encodedV2(t, v.SignedManifest), func(b []byte) error { _, e := protocol.DecodeSignedManifestV2(b); return e })
	removeRequiredFieldsV2(t, encodedV2(t, v.SignedAssignment), func(b []byte) error { _, e := protocol.DecodeSignedAssignmentV2(b); return e })
	removeRequiredFieldsV2(t, encodedV2(t, v.SignedManifest.Manifest), func(b []byte) error { var m protocol.ManifestV2; return protocol.DecodeJSON(b, &m) })
	removeRequiredFieldsV2(t, encodedV2(t, v.SignedAssignment.Assignment), func(b []byte) error { var a protocol.AssignmentV2; return protocol.DecodeJSON(b, &a) })
	for _, target := range []string{"scope", "limits"} {
		t.Run(target, func(t *testing.T) {
			var m map[string]json.RawMessage
			_ = json.Unmarshal(encodedV2(t, v.SignedManifest.Manifest), &m)
			removeRequiredFieldsV2(t, m[target], func(b []byte) error {
				copy := map[string]json.RawMessage{}
				for k, v := range m {
					copy[k] = v
				}
				copy[target] = b
				var output protocol.ManifestV2
				return protocol.DecodeJSON(encodedV2(t, copy), &output)
			})
		})
	}
	raw := encodedV2(t, v.SignedAssignment)
	for _, changed := range [][]byte{bytes.Replace(raw, []byte(`"schema":2`), []byte(`"SCHEMA":2`), 1), bytes.Replace(raw, []byte(`"schema":2`), []byte(`"schema":2,"SCHEMA":2`), 1), bytes.Replace(raw, []byte(`"schema":2`), []byte(`"schema":2,"\u0073chema":2`), 1)} {
		if _, e := protocol.DecodeSignedAssignmentV2(changed); e == nil {
			t.Fatal("case alias or duplicate assignment accepted")
		}
	}
}

func TestV2TransportByteLimitAndExplicitNegotiation(t *testing.T) {
	v := loadV2(t)
	raw := encodedV2(t, v.SignedManifest)
	for _, extra := range []int{0, 1} {
		padded := append(bytes.Clone(raw), bytes.Repeat([]byte(" "), protocol.MaxV2DocumentBytes-len(raw)+extra)...)
		_, e := protocol.DecodeSignedManifestV2(padded)
		if (e == nil) != (extra == 0) {
			t.Fatalf("boundary %d: %v", extra, e)
		}
	}
	v1host := v.Host
	v1host.Protocol = 1
	if e := protocol.VerifyManifestV2(v.SignedManifest, v.Payload, v.Roots, v1host, v.VerificationTime); e == nil {
		t.Fatal("v1 host implicitly negotiated v2")
	}
	var v1 protocol.SignedManifest
	if e := protocol.DecodeJSON(raw, &v1); e == nil {
		t.Fatal("v1 struct accepted grants sidecar")
	}
	for _, mutation := range []func(*protocol.ManifestV2){func(m *protocol.ManifestV2) { m.Schema = 1 }, func(m *protocol.ManifestV2) { m.Protocol = 1 }, func(m *protocol.ManifestV2) { m.GuestABI = 2 }, func(m *protocol.ManifestV2) { m.UISchema = 2 }} {
		m := v.SignedManifest.Manifest
		mutation(&m)
		if e := m.Validate(); e == nil {
			t.Fatal("unsupported profile accepted")
		}
	}
}

func TestV2AssignmentSignatureTransportIsCanonicalBase64(t *testing.T) {
	v := loadV2(t)
	text := base64.StdEncoding.EncodeToString(v.SignedAssignment.Signature)
	alphabet := "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
	padBits := []byte(text)
	padBits[len(padBits)-3] = alphabet[strings.IndexByte(alphabet, padBits[len(padBits)-3])+1]
	numbers := []uint64{}
	for _, b := range v.SignedAssignment.Signature {
		numbers = append(numbers, uint64(b))
	}
	for _, signature := range []any{numbers, text[:16] + "\n" + text[16:], string(padBits)} {
		raw := encodedV2(t, map[string]any{"assignment": v.SignedAssignment.Assignment, "signature": signature})
		if _, e := protocol.DecodeSignedAssignmentV2(raw); e == nil {
			t.Fatal("noncanonical signature transport accepted")
		}
	}
}

func TestV2ReplayRollbackDomainsAndArtifactReauthorization(t *testing.T) {
	v := loadV2(t)
	public, key, e := ed25519.GenerateKey(rand.Reader)
	if e != nil {
		t.Fatal(e)
	}
	v.Roots[1].PublicKey = public
	a := v.SignedAssignment.Assignment
	a.Sequence = 8
	s, e := protocol.SignAssignmentV2(a, key)
	if e != nil {
		t.Fatal(e)
	}
	if e = protocol.VerifyAssignmentV2(s, v.SignedManifest, v.Roots, v.Host, "beta", v.Installation, 7, v.VerificationTime); e != nil {
		t.Fatal("new assignment to retained old artifact rejected", e)
	}
	if e = protocol.VerifyAssignmentV2(s, v.SignedManifest, v.Roots, v.Host, "beta", v.Installation, 8, v.VerificationTime); e == nil {
		t.Fatal("replay accepted")
	}
	maximum := a
	maximum.Sequence = math.MaxUint64
	last, e := protocol.SignAssignmentV2(maximum, key)
	if e != nil {
		t.Fatal(e)
	}
	if e = protocol.VerifyAssignmentV2(last, v.SignedManifest, v.Roots, v.Host, "beta", v.Installation, math.MaxUint64-1, v.VerificationTime); e != nil {
		t.Fatal("maximum sequence rejected", e)
	}
	if e = protocol.VerifyAssignmentV2(last, v.SignedManifest, v.Roots, v.Host, "beta", v.Installation, math.MaxUint64, v.VerificationTime); e == nil {
		t.Fatal("maximum sequence replay accepted")
	}
	b, e := protocol.CanonicalCBOR(a)
	if e != nil {
		t.Fatal(e)
	}
	s.Signature = ed25519.Sign(key, append([]byte(protocol.AssignmentDomain), b...))
	if e = protocol.VerifyAssignmentV2(s, v.SignedManifest, v.Roots, v.Host, "beta", v.Installation, 7, v.VerificationTime); e == nil {
		t.Fatal("v1 signature domain accepted")
	}
	s, e = protocol.SignAssignmentV2(a, key)
	if e != nil {
		t.Fatal(e)
	}
	v.Roots[0].Revoked = true
	if e = protocol.VerifyAssignmentV2(s, v.SignedManifest, v.Roots, v.Host, "beta", v.Installation, 7, v.VerificationTime); e == nil {
		t.Fatal("new assignment bypassed revoked artifact signing authority")
	}
	v.Roots[0].Revoked = false
	v.Roots[0].NotAfterUnix = v.VerificationTime
	if e = protocol.VerifyAssignmentV2(s, v.SignedManifest, v.Roots, v.Host, "beta", v.Installation, 7, v.VerificationTime); e == nil {
		t.Fatal("new assignment bypassed expired artifact signing authority")
	}
	v.Roots[0].NotAfterUnix = 0
	for _, mutate := range []func(*protocol.AssignmentV2){func(a *protocol.AssignmentV2) { a.Scope.Organization = "another" }, func(a *protocol.AssignmentV2) { a.ArtifactSHA256 = protocol.Hash(nil) }, func(a *protocol.AssignmentV2) { a.Runtime = protocol.Hash(nil) }, func(a *protocol.AssignmentV2) { a.Channel = "production" }, func(a *protocol.AssignmentV2) { a.ReleaseID = "another" }} {
		changed := a
		mutate(&changed)
		signed, e := protocol.SignAssignmentV2(changed, key)
		if e != nil {
			t.Fatal(e)
		}
		if e = protocol.VerifyAssignmentV2(signed, v.SignedManifest, v.Roots, v.Host, "beta", v.Installation, 7, v.VerificationTime); e == nil {
			t.Fatal("assignment binding mismatch accepted")
		}
	}
	a.RolloutBasisPoints = 0
	s, e = protocol.SignAssignmentV2(a, key)
	if e != nil {
		t.Fatal(e)
	}
	if e = protocol.VerifyAssignmentV2(s, v.SignedManifest, v.Roots, v.Host, "beta", v.Installation, 7, v.VerificationTime); e == nil {
		t.Fatal("zero cohort accepted")
	}
}

func TestV2HostBoundsIntegrityAndGrantBinding(t *testing.T) {
	v := loadV2(t)
	for _, mutate := range []func(*protocol.Host){func(h *protocol.Host) { h.Runtime = protocol.Hash(nil) }, func(h *protocol.Host) { h.MaxPayloadBytes = 1 }, func(h *protocol.Host) { h.Limits.Fuel = 1 }, func(h *protocol.Host) { h.Limits.MemoryBytes = 1 }, func(h *protocol.Host) { h.Limits.StartupMilliseconds = 1 }, func(h *protocol.Host) { h.StateVersion = 2 }, func(h *protocol.Host) { h.CapabilityHashes = map[string]string{} }, func(h *protocol.Host) { h.Scope.Project = "another" }} {
		h := v.Host
		mutate(&h)
		if e := protocol.VerifyManifestV2(v.SignedManifest, v.Payload, v.Roots, h, v.VerificationTime); e == nil {
			t.Fatal("wrong host contract accepted")
		}
	}
	if e := protocol.VerifyManifestV2(v.SignedManifest, append(bytes.Clone(v.Payload), 0), v.Roots, v.Host, v.VerificationTime); e == nil {
		t.Fatal("extra payload byte accepted")
	}
	altered := bytes.Clone(v.Payload)
	altered[0] ^= 1
	if e := protocol.VerifyManifestV2(v.SignedManifest, altered, v.Roots, v.Host, v.VerificationTime); e == nil {
		t.Fatal("payload tamper accepted")
	}
	g := v.SignedManifest.Manifest.CapabilityGrants
	if e := g.Validate(map[string]string{protocol.HTTPGrantID: protocol.StorageGrantSHA256, protocol.StorageGrantID: protocol.StorageGrantSHA256}); e == nil {
		t.Fatal("signed capability map/schema binding lost")
	}
	g.Entries = []protocol.CapabilityGrant{}
	if e := g.Validate(v.Host.CapabilityHashes); e != nil {
		t.Fatal("empty grants should deny without inventing authority", e)
	}
}

func FuzzV2SignedManifestTransport(f *testing.F) {
	v := loadV2(f)
	f.Add(encodedV2(f, v.SignedManifest))
	f.Add([]byte(`{"manifest":{},"signature":""}`))
	f.Add([]byte(`{"manifest":{"schema":2,"SCHEMA":2},"signature":""}`))
	f.Fuzz(func(t *testing.T, data []byte) {
		s, e := protocol.DecodeSignedManifestV2(data)
		if e == nil {
			_ = protocol.VerifyManifestV2(s, v.Payload, v.Roots, v.Host, v.VerificationTime)
		}
	})
}
