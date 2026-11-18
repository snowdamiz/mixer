//go:build postgres_integration

package release

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"mixer/services/internal/testutil"
	"mixer/services/protocol"
)

func TestPostgresV3PublisherIncident(t *testing.T) {
	cfg, fixture, _, _ := pgFixture(t)
	fixture = fixture.Protocol3()
	cfg.Hosts = append(cfg.Hosts, fixture.Host)
	const oldBearer = "pg publisher"
	const newBearer = "TEST ONLY replacement publisher"
	const publishPath = v3Base + "/channels/beta/publish"
	const auditPath = v3Base + "/audit"
	offerPath := v2OfferPath(fixture, 3)

	client := &http.Client{Timeout: 7 * time.Second}
	defer client.CloseIdleConnections()
	request := func(server *httptest.Server, method, path, bearer, key string, value any) (int, []byte) {
		t.Helper()
		var raw []byte
		if value != nil {
			var err error
			raw, err = json.Marshal(value)
			if err != nil {
				t.Fatal(err)
			}
		}
		req, err := http.NewRequest(method, server.URL+path, bytes.NewReader(raw))
		if err != nil {
			t.Fatal(err)
		}
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("Idempotency-Key", key)
		if bearer != "" {
			req.Header.Set("Authorization", "Bearer "+bearer)
		}
		response, err := client.Do(req)
		if err != nil {
			t.Fatal(err)
		}
		defer response.Body.Close()
		raw, err = io.ReadAll(io.LimitReader(response.Body, 65536))
		if err != nil {
			t.Fatal(err)
		}
		if response.Header.Get("Cache-Control") != "no-store" {
			t.Errorf("%s %s omitted Cache-Control: no-store", method, path)
		}
		return response.StatusCode, raw
	}
	get := func(server *httptest.Server, path, bearer string, want int) []byte {
		t.Helper()
		code, body := request(server, "GET", path, bearer, "", nil)
		if code != want {
			t.Errorf("GET %s: got %d, want %d", path, code, want)
		}
		return body
	}
	mutate := func(server *httptest.Server, method, path, bearer, key string, body any, want int) []byte {
		t.Helper()
		code, raw := request(server, method, path, bearer, key, body)
		if code != want {
			t.Errorf("%s %s (%s): got %d, want %d; body: %s", method, path, key, code, want, raw)
		}
		return raw
	}
	publish := func(server *httptest.Server, bearer, key string, signed protocol.SignedAssignmentV3, want int) {
		t.Helper()
		mutate(server, "POST", publishPath, bearer, key, map[string]any{"signed_assignment": signed}, want)
	}
	offer := func(raw []byte) protocol.SignedAssignmentV3 {
		t.Helper()
		var value struct {
			Assignment protocol.SignedAssignmentV3 `json:"signed_assignment"`
			Artifact   string                      `json:"artifact_url"`
		}
		if err := protocol.DecodeJSON(raw, &value); err != nil {
			t.Fatal(err)
		}
		return value.Assignment
	}

	original := pgServer(t, cfg, nil)
	before := httptest.NewServer(original)
	t.Cleanup(before.Close)
	artifact, digest := v3Artifact(t, fixture, "publisher-incident")
	mutate(before, "PUT", v3Base+"/artifacts/"+digest, oldBearer, "incident-upload", artifact, 201)
	mutate(before, "POST", v3Base+"/releases/validate", oldBearer, "incident-validate", map[string]string{"artifact_sha256": digest}, 200)
	first := fixture.AssignmentV3(t, artifact.SignedManifest.Manifest, 1, 10000)
	publish(before, oldBearer, "incident-original", first, 200)
	if got := offer(get(before, offerPath, "", 200)); got.Assignment.Sequence != 1 || !bytes.Equal(got.Signature, first.Signature) {
		t.Fatal("baseline did not publish the original signed offer")
	}
	beforeAudit := get(before, auditPath, "pg reader", 200)
	before.Close()
	if err := original.Close(); err != nil {
		t.Fatal(err)
	}

	replacement := testutil.New(t).Protocol3()
	replacement.Roots[1].KeyID = "incident-replacement-assignment"
	cfg.Roots[1].Revoked = true
	cfg.Roots = append(cfg.Roots, replacement.Roots[1])
	cfg.Tokens[0].SHA256 = protocol.Hash([]byte(newBearer))
	cfg.Tokens[0].Actor = "replacement-publisher"
	recovered := pgServer(t, cfg, nil)
	after := httptest.NewServer(recovered)
	t.Cleanup(after.Close)
	t.Log("restarted a fresh loopback release listener on the same database with the old publisher bearer replaced and assignment root revoked")

	get(after, offerPath, "", 204)
	next := replacement.AssignmentV3(t, artifact.SignedManifest.Manifest, 2, 10000)
	publish(after, oldBearer, "incident-revoked-bearer", next, 401)
	oldSignedNext := fixture.AssignmentV3(t, artifact.SignedManifest.Manifest, 2, 10000)
	publish(after, newBearer, "incident-revoked-key", oldSignedNext, 409)
	if rejectedAudit := get(after, auditPath, "pg reader", 200); !bytes.Equal(rejectedAudit, beforeAudit) {
		t.Error("rejected incident operations changed publication audit history")
	}
	publish(after, newBearer, "incident-recovered", next, 200)
	if got := offer(get(after, offerPath, "", 200)); got.Assignment.Sequence != 2 || !bytes.Equal(got.Signature, next.Signature) {
		t.Error("recovery did not serve the new signed offer")
	}
	artifactPath := "/v3/artifacts/" + digest + "?organization=org-a&project=project-a"
	if got := get(after, artifactPath, "", 200); !bytes.Equal(got, mustMarshalIncidentArtifact(t, artifact)) {
		t.Error("recovery changed signed artifact bytes")
	}
	t.Log("revoked bearer 401, revoked-key write 409, unchanged audit on denied writes, sequence-2 recovery and artifact delivery checked")
}

func mustMarshalIncidentArtifact(t *testing.T, artifact ArtifactV3) []byte {
	t.Helper()
	value, err := json.Marshal(artifact)
	if err != nil {
		t.Fatal(err)
	}
	return value
}
