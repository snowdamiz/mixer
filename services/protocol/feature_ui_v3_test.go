package protocol_test

import (
	"slices"
	"strings"
	"testing"

	"mixer/services/internal/testutil"
	"mixer/services/protocol"
)

func TestFeatureUIEnrollmentBindsInstalledDescriptor(t *testing.T) {
	f, pin := testutil.FeatureUI(t)
	p, err := protocol.NewFeatureUIV3(pin)
	if err != nil {
		t.Fatal(err)
	}
	if p.Scope() != f.Host.Scope || p.Runtime() != f.Host.Runtime {
		t.Fatal("enrolled identity differs from installed identity")
	}
	for _, tc := range []struct {
		name   string
		change func(*protocol.FeatureUIEnrollment)
		want   string
	}{
		{"fingerprint", func(p *protocol.FeatureUIEnrollment) { p.Fingerprint = protocol.Hash(nil) }, "fingerprint mismatch"},
		{"root bytes", func(p *protocol.FeatureUIEnrollment) { p.TrustRootsJSON = append(slices.Clone(p.TrustRootsJSON), '\n') }, "trust roots digest mismatch"},
		{"app scope", func(p *protocol.FeatureUIEnrollment) { p.Scope.App = "other-app" }, "descriptor scope mismatch"},
		{"root scope", func(p *protocol.FeatureUIEnrollment) {
			roots := slices.Clone(f.Roots)
			roots[0].Scope.App = "other-app"
			*p = testutil.RebindFeatureUIRoots(t, *p, roots)
		}, "root scope mismatch"},
		{"namespace", func(p *protocol.FeatureUIEnrollment) { p.StoragePolicy.Namespace = "other" }, "storage grant digest mismatch"},
		{"write", func(p *protocol.FeatureUIEnrollment) { p.StoragePolicy.Operations = []string{"get", "set"} }, "operations [get]"},
		{"absent operations", func(p *protocol.FeatureUIEnrollment) { p.StoragePolicy.Operations = nil }, "operations [get]"},
		{"duplicate operation", func(p *protocol.FeatureUIEnrollment) { p.StoragePolicy.Operations = []string{"get", "get"} }, "operations [get]"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			bad := pin
			tc.change(&bad)
			got, err := protocol.NewFeatureUIV3(bad)
			if got != nil || err == nil || !strings.Contains(err.Error(), tc.want) {
				t.Fatalf("enrollment error = %v, want %q", err, tc.want)
			}
		})
	}
}

func TestFeatureUIRequiresExplicitVerifier(t *testing.T) {
	f, pin := testutil.FeatureUI(t)
	p, err := protocol.NewFeatureUIV3(pin)
	if err != nil {
		t.Fatal(err)
	}
	payload := []byte("signed feature UI payload")
	signed := f.FeatureUIManifest(t, payload, "test-feature-ui")
	assignment := f.AssignmentV3(t, signed.Manifest, 1, 10000)
	const now = 101
	if err := p.VerifyManifest(signed, payload, now); err != nil {
		t.Fatal(err)
	}
	if err := p.VerifyAssignment(assignment, signed, "beta", 0, now); err != nil {
		t.Fatal(err)
	}
	if protocol.ValidateHostV3(f.Host) == nil || signed.Manifest.Validate() == nil ||
		protocol.VerifyManifestV3(signed, payload, f.Roots, f.Host, now) == nil ||
		protocol.VerifyAssignmentHeaderV3(assignment, signed, f.Roots, f.Host, "beta", 0, now) == nil {
		t.Fatal("default v3 admitted raw UI3")
	}
	if _, err := protocol.SignManifestV3(signed.Manifest, f.ArtifactKey); err == nil {
		t.Fatal("default v3 signer admitted UI3")
	}

	crossApp := signed.Manifest
	crossApp.Scope.App = "other-app"
	if err := p.VerifyManifest(testutil.SignFeatureUIManifest(t, crossApp, f.ArtifactKey), payload, now); err == nil {
		t.Fatal("accepted a correctly signed manifest for a different app")
	}
	wrongNamespace := f.FeatureUIManifest(t, payload, "wrong-namespace").Manifest
	wrongNamespace.CapabilityGrants.Entries[0].Namespaces = []string{"other"}
	if err := p.VerifyManifest(testutil.SignFeatureUIManifest(t, wrongNamespace, f.ArtifactKey), payload, now); err == nil {
		t.Fatal("accepted a correctly signed manifest for a different namespace")
	}
	crossAssignment := assignment.Assignment
	crossAssignment.Scope.App = "other-app"
	resigned, err := protocol.SignAssignmentV3(crossAssignment, f.AssignmentKey)
	if err != nil {
		t.Fatal(err)
	}
	if err := p.VerifyAssignment(resigned, signed, "beta", 0, now); err == nil {
		t.Fatal("accepted a correctly signed assignment for a different app")
	}
}
