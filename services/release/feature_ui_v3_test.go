package release

import (
	"bytes"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"mixer/services/internal/testutil"
	"mixer/services/protocol"
)

func TestFeatureUIServiceRejectsRawHostAndInvalidEnrollment(t *testing.T) {
	f, pin := testutil.FeatureUI(t)
	cfg := v3Config(t, testutil.New(t))
	cfg.Hosts = append(cfg.Hosts, f.Host)
	if err := ValidateConfig(cfg); err == nil {
		t.Fatal("raw UI3 host registered without enrollment")
	}
	cfg.Hosts = cfg.Hosts[:len(cfg.Hosts)-1]
	cfg.FeatureUI = &pin
	if err := ValidateConfig(cfg); err != nil {
		t.Fatal(err)
	}
	wire := string(testutil.JSON(t, cfg))
	for _, bad := range []string{
		strings.Replace(wire, `"feature_ui_v3":{`, `"feature_ui_v3":{"storage_policy_sha256":"unused",`, 1),
		strings.Replace(wire, `"storage_policy":{`, `"storage_policy":{"readable_keys":["draft"],`, 1),
	} {
		var decoded Config
		if bad == wire || protocol.DecodeJSON([]byte(bad), &decoded) == nil {
			t.Fatal("accepted obsolete storage enrollment fields")
		}
	}
	for _, tc := range []struct {
		name   string
		change func(*protocol.FeatureUIEnrollment)
	}{
		{"fingerprint", func(p *protocol.FeatureUIEnrollment) { p.Fingerprint = protocol.Hash(nil) }},
		{"roots", func(p *protocol.FeatureUIEnrollment) { p.TrustRootsJSON = append(bytes.Clone(p.TrustRootsJSON), '\n') }},
		{"scope", func(p *protocol.FeatureUIEnrollment) { p.Scope.App = "other-app" }},
		{"namespace", func(p *protocol.FeatureUIEnrollment) { p.StoragePolicy.Namespace = "other" }},
		{"wrong ops", func(p *protocol.FeatureUIEnrollment) { p.StoragePolicy.Operations = []string{"set"} }},
	} {
		t.Run(tc.name, func(t *testing.T) {
			bad := pin
			tc.change(&bad)
			cfg.FeatureUI = &bad
			if s, err := New(cfg); err == nil {
				s.Close()
				t.Fatal("started with invalid enrollment")
			}
		})
	}
}

func TestFeatureUIReleaseRequiresEnrollmentAfterRestart(t *testing.T) {
	f, pin := testutil.FeatureUI(t)
	cfg := v3Config(t, testutil.New(t))
	payload := []byte("feature UI release")
	artifact := ArtifactV3{f.FeatureUIManifest(t, payload, "feature-ui"), payload}
	digest, err := protocol.ManifestDigestV3(artifact.SignedManifest.Manifest)
	if err != nil {
		t.Fatal(err)
	}
	manifest := artifact.SignedManifest.Manifest
	first := f.AssignmentV3(t, manifest, 1, 5000)
	promote := f.AssignmentV3(t, manifest, 2, 10000)
	rollback := f.AssignmentV3(t, manifest, 3, 10000)
	halt := f.AssignmentV3(t, manifest, 4, 0)
	artifactPath := v3Base + "/artifacts/" + digest
	publicPath := "/v3/artifacts/" + digest + "?organization=org-a&project=project-a"
	updatePath := v2OfferPath(f, 3)
	validate := map[string]string{"artifact_sha256": digest}
	haltBody := map[string]any{
		"signed_assignment": halt,
		"health":            RolloutHealth{Sequence: 3, AdverseSignals: 1},
	}
	open := func(cfg Config) *Server {
		t.Helper()
		s, err := New(cfg)
		if err != nil {
			t.Fatal(err)
		}
		t.Cleanup(func() { _ = s.Close() })
		return s
	}
	close := func(s *Server) {
		t.Helper()
		if err := s.Close(); err != nil {
			t.Fatal(err)
		}
	}
	upload := func(s http.Handler, key string, a ArtifactV3) *httptest.ResponseRecorder {
		t.Helper()
		d, err := protocol.ManifestDigestV3(a.SignedManifest.Manifest)
		if err != nil {
			t.Fatal(err)
		}
		return v2Request(s, "PUT", v3Base+"/artifacts/"+d, key, v3Publisher, a)
	}
	legacyHost := f.Host
	legacyHost.UISchema = 1
	legacyFallback := cfg
	legacyFallback.Hosts = append(append([]protocol.Host(nil), cfg.Hosts...), legacyHost)
	legacyFallback.Roots = f.Roots
	// A matching raw UI1 registration still cannot authorize a signed UI3 envelope.
	s := open(legacyFallback)
	v2Status(t, v2Request(s, "PUT", artifactPath, "upload-ui3", v3Publisher, artifact), 422)
	close(s)

	cfg.FeatureUI = &pin
	s = open(cfg)
	for _, tc := range []struct {
		name   string
		change func(*protocol.ManifestV3)
	}{
		{"wrong-app", func(m *protocol.ManifestV3) { m.Scope.App = "other-app" }},
		{"wrong-runtime", func(m *protocol.ManifestV3) { m.Runtime = protocol.Hash(nil) }},
		{"wrong-namespace", func(m *protocol.ManifestV3) { m.CapabilityGrants.Entries[0].Namespaces = []string{"other"} }},
		{"wrong-storage-method", func(m *protocol.ManifestV3) { m.CapabilityGrants.Entries[0].Methods = []string{"SET"} }},
	} {
		t.Run(tc.name, func(t *testing.T) {
			bad := f.FeatureUIManifest(t, payload, "feature-ui").Manifest
			tc.change(&bad)
			v2Status(t, upload(s, tc.name, ArtifactV3{testutil.SignFeatureUIManifest(t, bad, f.ArtifactKey), payload}), 422)
		})
	}
	v2Status(t, v2Request(s, "PUT", artifactPath, "upload-ui3", v3Publisher, artifact), 201)
	v2Status(t, v2Request(s, "POST", v3Base+"/releases/validate", "validate-ui3", v3Publisher, validate), 200)
	cross := first.Assignment
	cross.Scope.App = "other-app"
	crossApp, err := protocol.SignAssignmentV3(cross, f.AssignmentKey)
	if err != nil {
		t.Fatal(err)
	}
	v2Status(t, v3Publish(s, "publish", "other-app-assignment", v3Publisher, crossApp), 422)

	v2Status(t, v3Publish(s, "publish", "publish-ui3", v3Publisher, first), 200)
	v2Status(t, v3Publish(s, "promote", "promote-ui3", v3Publisher, promote), 200)
	v2Status(t, v3Publish(s, "rollback", "rollback-ui3", v3Publisher, rollback), 200)
	v2Status(t, v2Request(s, "POST", v3Base+"/channels/beta/halt", "halt-ui3", v3Publisher, haltBody), 200)
	// Restore an active offer so HTTP 204 after removal cannot be a rollout result.
	active := f.AssignmentV3(t, manifest, 5, 10000)
	v2Status(t, v3Publish(s, "publish", "active-ui3", v3Publisher, active), 200)
	expectedOffer := v2Request(s, "GET", updatePath, "", "", nil)
	v2Status(t, expectedOffer, 200)
	v2Status(t, v2Request(s, "GET", publicPath, "", "", nil), 200)
	v2Status(t, v2Request(s, "GET", artifactPath, "", v3Publisher, nil), 200)
	before := v3State(t, cfg)
	close(s)

	unenrolled := cfg
	unenrolled.FeatureUI = nil
	for _, tc := range []struct {
		name string
		cfg  Config
	}{
		{"no-enrollment", unenrolled},
		{"legacy-host-at-same-fingerprint", legacyFallback},
	} {
		t.Run(tc.name, func(t *testing.T) {
			s := open(tc.cfg)
			defer close(s)
			v2Status(t, v2Request(s, "PUT", artifactPath, "upload-ui3", v3Publisher, artifact), 422)
			v2Status(t, v2Request(s, "POST", v3Base+"/releases/validate", "validate-ui3", v3Publisher, validate), 422)
			v2Status(t, v3Publish(s, "publish", "publish-ui3", v3Publisher, first), 422)
			v2Status(t, v3Publish(s, "promote", "promote-ui3", v3Publisher, promote), 422)
			v2Status(t, v3Publish(s, "rollback", "rollback-ui3", v3Publisher, rollback), 422)
			v2Status(t, v2Request(s, "POST", v3Base+"/channels/beta/halt", "halt-ui3", v3Publisher, haltBody), 422)
			v2Status(t, v3Publish(s, "publish", "fresh-ui3", v3Publisher, f.AssignmentV3(t, manifest, 6, 10000)), 422)
			v2Status(t, v2Request(s, "GET", updatePath, "", "", nil), 204)
			v2Status(t, v2Request(s, "GET", publicPath, "", "", nil), 404)
			v2Status(t, v2Request(s, "GET", artifactPath, "", v3Publisher, nil), 404)
			if !bytes.Equal(before, v3State(t, tc.cfg)) {
				t.Fatal("rejected mutations changed the durable release state")
			}
		})
	}

	s = open(cfg)
	restored := v2Request(s, "GET", updatePath, "", "", nil)
	v2Status(t, restored, 200)
	if !bytes.Equal(restored.Body.Bytes(), expectedOffer.Body.Bytes()) {
		t.Fatal("re-enrollment changed the stored offer")
	}
}
