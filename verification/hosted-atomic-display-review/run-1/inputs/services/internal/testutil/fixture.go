// Package testutil provides originally authored ephemeral protocol fixtures.
package testutil

import (
	"crypto/ed25519"
	"crypto/rand"
	"strings"
	"testing"

	"mixer/services/protocol"
)

type Fixture struct {
	Host          protocol.Host
	Roots         []protocol.Root
	ArtifactKey   ed25519.PrivateKey
	AssignmentKey ed25519.PrivateKey
}

func New(t testing.TB) Fixture {
	t.Helper()
	pub, priv, e := ed25519.GenerateKey(rand.Reader)
	if e != nil {
		t.Fatal(e)
	}
	apub, apriv, e := ed25519.GenerateKey(rand.Reader)
	if e != nil {
		t.Fatal(e)
	}
	scope := protocol.Scope{Organization: "org-a", Project: "project-a", App: "fieldlog", Environment: "development", Platform: "ios"}
	host := protocol.Host{Scope: scope, Runtime: protocol.Hash([]byte("runtime-v1")), Protocol: 1, GuestABI: 1, UISchema: 1, CapabilityHashes: map[string]string{"state": protocol.Hash([]byte("state-v1"))}, StateVersion: 1, MaxPayloadBytes: protocol.MaxPayloadBytes, Limits: protocol.Limits{MemoryBytes: 64 * 1024 * 1024, Fuel: 1000000, StartupMilliseconds: 5000}}
	roots := []protocol.Root{{KeyID: "artifact-key", PublicKey: pub, Scope: scope, Artifact: true}, {KeyID: "assignment-key", PublicKey: apub, Scope: scope, Assignment: true}}
	return Fixture{host, roots, priv, apriv}
}
func (f Fixture) Manifest(t testing.TB, payload []byte, id string) protocol.SignedManifest {
	t.Helper()
	m := protocol.Manifest{Schema: 1, Scope: f.Host.Scope, ReleaseID: id, SourceCommit: strings.Repeat("a", 40), ProvenanceID: "test-build-1", Runtime: f.Host.Runtime, Protocol: 1, GuestABI: 1, UISchema: 1, CapabilityHashes: map[string]string{"state": f.Host.CapabilityHashes["state"]}, StateMin: 1, StateMax: 1, PayloadSHA256: protocol.Hash(payload), CompressedBytes: uint64(len(payload)), ExpandedBytes: uint64(len(payload)), Compression: "none", AssetHashes: map[string]string{}, SourceMapSHA256: protocol.Hash(nil), Limits: protocol.Limits{MemoryBytes: 1024 * 1024, Fuel: 1000, StartupMilliseconds: 1000}, KeyID: "artifact-key", CreatedAtUnix: 100}
	s, e := protocol.SignManifest(m, f.ArtifactKey)
	if e != nil {
		t.Fatal(e)
	}
	return s
}
func (f Fixture) Assignment(t testing.TB, m protocol.Manifest, seq, rollout uint64) protocol.SignedAssignment {
	t.Helper()
	digest, e := protocol.ManifestDigest(m)
	if e != nil {
		t.Fatal(e)
	}
	a := protocol.Assignment{Schema: 1, Scope: m.Scope, Channel: "beta", Cohort: "sha256-v1", RolloutBasisPoints: rollout, Sequence: seq, ReleaseID: m.ReleaseID, ArtifactSHA256: digest, Runtime: m.Runtime, KeyID: "assignment-key", CreatedAtUnix: 100}
	s, e := protocol.SignAssignment(a, f.AssignmentKey)
	if e != nil {
		t.Fatal(e)
	}
	return s
}
