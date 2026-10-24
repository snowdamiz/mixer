package protocol_test

import (
	"bytes"
	"crypto/ed25519"
	"encoding/hex"
	"fmt"
	"math"
	"os"
	"testing"

	"mixer/services/internal/testutil"
	"mixer/services/protocol"
)

func TestStaticCrossLanguageSignedVector(t *testing.T) {
	raw, e := os.ReadFile("testdata/signed-release-v1.json")
	if e != nil {
		t.Fatal(e)
	}
	var v struct {
		TestOnly          bool                      `json:"test_only"`
		Description       string                    `json:"description"`
		SignedManifest    protocol.SignedManifest   `json:"signed_manifest"`
		SignedAssignment  protocol.SignedAssignment `json:"signed_assignment"`
		Roots             []protocol.Root           `json:"roots"`
		Host              protocol.Host             `json:"host"`
		Payload           []byte                    `json:"payload"`
		ManifestCBORHex   string                    `json:"manifest_cbor_hex"`
		AssignmentCBORHex string                    `json:"assignment_cbor_hex"`
		ArtifactSHA256    string                    `json:"artifact_sha256"`
		Installation      string                    `json:"installation"`
		CohortBucket      uint64                    `json:"cohort_bucket"`
		VerificationTime  uint64                    `json:"verification_time_unix"`
		LastSequence      uint64                    `json:"last_sequence"`
	}
	if e = protocol.DecodeJSON(raw, &v); e != nil {
		t.Fatal(e)
	}
	if !v.TestOnly {
		t.Fatal("fixture purpose missing")
	}
	b, e := protocol.CanonicalCBOR(v.SignedManifest.Manifest)
	if e != nil || hex.EncodeToString(b) != v.ManifestCBORHex || protocol.Hash(b) != v.ArtifactSHA256 {
		t.Fatal("manifest vector changed", e)
	}
	b, e = protocol.CanonicalCBOR(v.SignedAssignment.Assignment)
	if e != nil || hex.EncodeToString(b) != v.AssignmentCBORHex {
		t.Fatal("assignment vector changed", e)
	}
	if e = protocol.VerifyManifest(v.SignedManifest, v.Payload, v.Roots, v.Host, v.VerificationTime); e != nil {
		t.Fatal(e)
	}
	if e = protocol.VerifyAssignment(v.SignedAssignment, v.SignedManifest.Manifest, v.Roots, v.Host, "beta", v.Installation, v.LastSequence, v.VerificationTime); e != nil {
		t.Fatal(e)
	}
	bucket, e := protocol.Cohort(v.SignedAssignment.Assignment, v.Installation)
	if e != nil || bucket != v.CohortBucket {
		t.Fatal("cohort vector changed", e)
	}
}

func TestCanonicalRFC8949Subset(t *testing.T) {
	// Hand-written vectors from the CBOR encoding rules; no imported corpus.
	cases := []struct {
		v   any
		hex string
	}{{uint64(0), "00"}, {uint64(23), "17"}, {uint64(24), "1818"}, {uint64(255), "18ff"}, {uint64(256), "190100"}, {uint64(65536), "1a00010000"}, {uint64(math.MaxUint64), "1bffffffffffffffff"}, {"IETF", "6449455446"}, {true, "f5"}, {[]uint64{1, 24}, "82011818"}, {map[string]uint64{"b": 1, "a": 2}, "a2616102616201"}, {map[string]string{}, "a0"}}
	for _, c := range cases {
		b, e := protocol.CanonicalCBOR(c.v)
		if e != nil || hex.EncodeToString(b) != c.hex {
			t.Fatalf("%v: %x %v", c.v, b, e)
		}
	}
	for _, bad := range []any{float64(1), int64(-1), map[int]string{1: "x"}, nil, "\xff"} {
		if _, e := protocol.CanonicalCBOR(bad); e == nil {
			t.Fatalf("accepted unsupported %T", bad)
		}
	}
	// Encoded-key ordering is deterministic regardless of insertion order.
	a, _ := protocol.CanonicalCBOR(map[string]uint64{"aa": 1, "b": 2})
	if hex.EncodeToString(a) != "a261620262616101" {
		t.Fatalf("key order: %x", a)
	}
}

func TestArtifactTamperAndCompatibility(t *testing.T) {
	f := testutil.New(t)
	payload := []byte("independently authored guest payload")
	sm := f.Manifest(t, payload, "release-1")
	if e := protocol.VerifyManifest(sm, payload, f.Roots, f.Host, 100); e != nil {
		t.Fatal(e)
	}
	b, _ := protocol.CanonicalCBOR(sm.Manifest)
	if !ed25519.Verify(f.Roots[0].PublicKey, append([]byte(protocol.ArtifactDomain), b...), sm.Signature) {
		t.Fatal("signature does not cover documented bytes")
	}
	if ed25519.Verify(f.Roots[0].PublicKey, append([]byte(protocol.AssignmentDomain), b...), sm.Signature) {
		t.Fatal("domains interchangeable")
	}
	cases := map[string]func(*protocol.Manifest){"app": func(m *protocol.Manifest) { m.Scope.App = "other" }, "tenant": func(m *protocol.Manifest) { m.Scope.Organization = "org-b" }, "environment": func(m *protocol.Manifest) { m.Scope.Environment = "production" }, "platform": func(m *protocol.Manifest) { m.Scope.Platform = "android" }, "runtime": func(m *protocol.Manifest) { m.Runtime = protocol.Hash(nil) }, "protocol": func(m *protocol.Manifest) { m.Protocol = 2 }, "abi": func(m *protocol.Manifest) { m.GuestABI = 2 }, "ui": func(m *protocol.Manifest) { m.UISchema = 2 }, "capability": func(m *protocol.Manifest) { m.CapabilityHashes = map[string]string{} }, "state": func(m *protocol.Manifest) { m.StateMin = 2; m.StateMax = 2 }, "compression": func(m *protocol.Manifest) { m.Compression = "gzip" }, "size": func(m *protocol.Manifest) { m.ExpandedBytes++ }, "oversize": func(m *protocol.Manifest) {
		m.ExpandedBytes = protocol.MaxPayloadBytes + 1
		m.CompressedBytes = m.ExpandedBytes
	}, "limit": func(m *protocol.Manifest) { m.Limits.Fuel = f.Host.Limits.Fuel + 1 }, "source": func(m *protocol.Manifest) { m.SourceCommit = "junk" }, "asset": func(m *protocol.Manifest) { m.AssetHashes = map[string]string{"image": protocol.Hash(nil)} }, "key": func(m *protocol.Manifest) { m.KeyID = "unknown" }, "provenance": func(m *protocol.Manifest) { m.ProvenanceID = "changed" }}
	for name, change := range cases {
		t.Run(name, func(t *testing.T) {
			tampered := sm
			change(&tampered.Manifest)
			if e := protocol.VerifyManifest(tampered, payload, f.Roots, f.Host, 100); e == nil {
				t.Fatal("accepted tampered/incompatible manifest")
			}
		})
	}
	for _, p := range [][]byte{[]byte("changed"), append(append([]byte{}, payload...), 0)} {
		if protocol.VerifyManifest(sm, p, f.Roots, f.Host, 100) == nil {
			t.Fatal("accepted payload tamper")
		}
	}
	bad := sm
	bad.Signature = bytes.Repeat([]byte{0}, 64)
	if protocol.VerifyManifest(bad, payload, f.Roots, f.Host, 100) == nil {
		t.Fatal("accepted bad signature")
	}
	for _, root := range []protocol.Root{{KeyID: f.Roots[0].KeyID, PublicKey: f.Roots[0].PublicKey, Scope: f.Host.Scope, Assignment: true}, {KeyID: f.Roots[0].KeyID, PublicKey: f.Roots[0].PublicKey, Scope: f.Host.Scope, Artifact: true, Revoked: true}, {KeyID: f.Roots[0].KeyID, PublicKey: f.Roots[0].PublicKey, Scope: f.Host.Scope, Artifact: true, NotAfterUnix: 100}, {KeyID: f.Roots[0].KeyID, PublicKey: f.Roots[0].PublicKey, Scope: f.Host.Scope, Artifact: true, NotBeforeUnix: 101}} {
		if protocol.VerifyManifest(sm, payload, []protocol.Root{root}, f.Host, 100) == nil {
			t.Fatal("accepted denied authority")
		}
	}
}

func TestAssignmentReplayRollbackAndStableCohort(t *testing.T) {
	f := testutil.New(t)
	old := f.Manifest(t, []byte("old"), "r1")
	newer := f.Manifest(t, []byte("new"), "r2")
	a1 := f.Assignment(t, old.Manifest, 1, 10000)
	a2 := f.Assignment(t, newer.Manifest, 2, 10000)
	rollback := f.Assignment(t, old.Manifest, 3, 10000)
	for _, c := range []struct {
		a    protocol.SignedAssignment
		m    protocol.Manifest
		last uint64
	}{{a1, old.Manifest, 0}, {a2, newer.Manifest, 1}, {rollback, old.Manifest, 2}} {
		if e := protocol.VerifyAssignment(c.a, c.m, f.Roots, f.Host, "beta", "install-1", c.last, 100); e != nil {
			t.Fatal(e)
		}
	}
	if protocol.VerifyAssignment(a1, old.Manifest, f.Roots, f.Host, "beta", "install-1", 2, 100) == nil {
		t.Fatal("accepted replay rollback")
	}
	if protocol.VerifyAssignment(rollback, newer.Manifest, f.Roots, f.Host, "beta", "install-1", 2, 100) == nil {
		t.Fatal("cross artifact binding")
	}
	if protocol.VerifyAssignment(rollback, old.Manifest, f.Roots, f.Host, "production", "install-1", 2, 100) == nil {
		t.Fatal("channel substitution")
	}
	a := a1
	a.Assignment.RolloutBasisPoints = 9999
	if protocol.VerifyAssignmentHeader(a, old.Manifest, f.Roots, f.Host, "beta", 0, 100) == nil {
		t.Fatal("unsigned rollout edit")
	}
	first := f.Assignment(t, old.Manifest, 4, 1000)
	expanded := f.Assignment(t, newer.Manifest, 5, 7500)
	eligible := 0
	for i := 0; i < 1000; i++ {
		id := fmt.Sprintf("install-%d", i)
		if protocol.Eligible(first.Assignment, id) {
			eligible++
			if !protocol.Eligible(expanded.Assignment, id) {
				t.Fatal("rollout expansion lost cohort")
			}
		}
	}
	if eligible < 50 || eligible > 150 {
		t.Fatalf("implausible cohort count %d", eligible)
	}
	if protocol.Eligible(first.Assignment, "../secret") {
		t.Fatal("unbounded identifier")
	}
	zero := f.Assignment(t, old.Manifest, 6, 0)
	if protocol.VerifyAssignment(zero, old.Manifest, f.Roots, f.Host, "beta", "install-1", 5, 100) == nil {
		t.Fatal("zero percent eligible")
	}
}

func TestStrictTransportJSON(t *testing.T) {
	for _, input := range []string{`{"schema":1,"schema":2}`, `{"scope":{"app":"a","app":"b"}}`, `{"unknown":1}`, `{} {}`, `{"schema":-1}`, `{"schema":1.1}`, `{"schema":18446744073709551616}`, `{"capability_hashes":null}`, "{\"release_id\":\"\xff\"}"} {
		var m protocol.Manifest
		if protocol.DecodeJSON([]byte(input), &m) == nil {
			t.Fatalf("accepted %s", input)
		}
	}
	// Numeric precision is independent of the closed Assignment shape. A partial
	// assignment is no longer a valid protocol document.
	var a struct {
		Sequence uint64 `json:"sequence"`
	}
	if e := protocol.DecodeJSON([]byte(`{"sequence":18446744073709551615}`), &a); e != nil || a.Sequence != math.MaxUint64 {
		t.Fatal("uint64 precision lost", e)
	}
}

func FuzzStrictJSONNeverPanics(f *testing.F) {
	f.Add([]byte(`{"schema":1}`))
	f.Add([]byte(`{"scope":{"app":"a"}}`))
	f.Fuzz(func(t *testing.T, b []byte) {
		if len(b) > 64*1024 {
			return
		}
		var m protocol.Manifest
		if protocol.DecodeJSON(b, &m) == nil {
			_, _ = protocol.CanonicalCBOR(m)
			_ = m.Validate()
		}
	})
}
