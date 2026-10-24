package testutil

import (
	"maps"
	"strings"
	"testing"

	"mixer/services/protocol"
)

// Protocol3 is a synthetic installed host for service tests, not native identity.
func (f Fixture) Protocol3() Fixture {
	f.Host.Protocol = 3
	f.Host.GuestABI = 2
	f.Host.Runtime = protocol.Hash([]byte("TEST ONLY explicit HTTP protocol3 runtime"))
	f.Host.CapabilityHashes = map[string]string{protocol.HTTPGrantID: protocol.HTTPGrantSHA256, protocol.StorageGrantID: protocol.StorageGrantSHA256}
	f.Host.MaxPayloadBytes = protocol.MaxV3PayloadBytes
	f.Host.Limits = protocol.Limits{MemoryBytes: protocol.MaxV3MemoryBytes, Fuel: protocol.MaxV3Fuel, StartupMilliseconds: 5000}
	return f
}
func (f Fixture) ManifestV3(t testing.TB, payload []byte, id string) protocol.SignedManifestV3 {
	t.Helper()
	grants := protocol.CapabilityGrants{Schema: 1, SchemaSHA256: protocol.GrantSchemaSHA256, Entries: []protocol.CapabilityGrant{
		{CapabilityID: protocol.HTTPGrantID, SchemaSHA256: protocol.HTTPGrantSHA256, Permissions: []string{"network.https"}, Origins: []string{"https://api.example.test"}, Methods: []string{"GET"}, Namespaces: []string{}},
		{CapabilityID: protocol.StorageGrantID, SchemaSHA256: protocol.StorageGrantSHA256, Permissions: []string{"storage.appPrivate"}, Origins: []string{}, Methods: []string{}, Namespaces: []string{"Drafts", "drafts"}},
	}}
	m := protocol.ManifestV3{Schema: 3, Scope: f.Host.Scope, ReleaseID: id, SourceCommit: strings.Repeat("a", 40), ProvenanceID: "TEST-ONLY-http-v3", Runtime: f.Host.Runtime, Protocol: 3, GuestABI: 2, UISchema: 1, CapabilityHashes: maps.Clone(f.Host.CapabilityHashes), CapabilityGrants: grants, StateMin: f.Host.StateVersion, StateMax: f.Host.StateVersion, PayloadSHA256: protocol.Hash(payload), CompressedBytes: uint64(len(payload)), ExpandedBytes: uint64(len(payload)), Compression: "none", AssetHashes: map[string]string{}, SourceMapSHA256: protocol.Hash(nil), Limits: protocol.Limits{MemoryBytes: 1048576, Fuel: 1000, StartupMilliseconds: 1000}, KeyID: f.Roots[0].KeyID, CreatedAtUnix: 100}
	signed, e := protocol.SignManifestV3(m, f.ArtifactKey)
	if e != nil {
		t.Fatal(e)
	}
	return signed
}
func (f Fixture) AssignmentV3(t testing.TB, m protocol.ManifestV3, sequence, rollout uint64) protocol.SignedAssignmentV3 {
	t.Helper()
	digest, e := protocol.ManifestDigestV3(m)
	if e != nil {
		t.Fatal(e)
	}
	a := protocol.AssignmentV3{Schema: 3, Scope: m.Scope, Channel: "beta", Cohort: "sha256-v1", RolloutBasisPoints: rollout, Sequence: sequence, ReleaseID: m.ReleaseID, ArtifactSHA256: digest, Runtime: m.Runtime, KeyID: f.Roots[1].KeyID, CreatedAtUnix: 100}
	signed, e := protocol.SignAssignmentV3(a, f.AssignmentKey)
	if e != nil {
		t.Fatal(e)
	}
	return signed
}
