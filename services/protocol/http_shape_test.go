package protocol_test

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"

	"mixer/services/internal/testutil"
	"mixer/services/protocol"
	"mixer/services/release"
)

func TestSharedJSONStrictShapeRejectsHTTPAliasesWithoutMutation(t *testing.T) {
	f := testutil.New(t)
	token := "TEST ONLY wire shape token"
	server, e := release.New(release.Config{DeveloperMode: true, Listen: "127.0.0.1:0", DataDirectory: t.TempDir(), Roots: f.Roots, Hosts: []protocol.Host{f.Host}, Tokens: []release.Token{{SHA256: protocol.Hash([]byte(token)), Role: "publisher", Organization: f.Host.Scope.Organization, Project: f.Host.Scope.Project, Actor: "wire-test"}}})
	if e != nil {
		t.Fatal(e)
	}
	t.Cleanup(func() {
		if e := server.Close(); e != nil {
			t.Error(e)
		}
	})
	payload := []byte("original signed local protocol HTTP shape fixture")
	signed := f.Manifest(t, payload, "wire-http")
	artifact := release.Artifact{SignedManifest: signed, Payload: payload}
	digest, e := protocol.ManifestDigest(signed.Manifest)
	if e != nil {
		t.Fatal(e)
	}
	path := "/v1/orgs/" + f.Host.Scope.Organization + "/projects/" + f.Host.Scope.Project
	request := func(method, url, key string, body []byte) *httptest.ResponseRecorder {
		r := httptest.NewRequest(method, url, bytes.NewReader(body))
		r.Header.Set("Content-Type", "application/json")
		r.Header.Set("Authorization", "Bearer "+token)
		r.Header.Set("Idempotency-Key", key)
		w := httptest.NewRecorder()
		server.ServeHTTP(w, r)
		return w
	}
	base := encodedV2(t, artifact)
	cases := []struct {
		name   string
		change func(map[string]json.RawMessage)
	}{
		{"alternate-signed-manifest", func(v map[string]json.RawMessage) {
			v["Signed_Manifest"] = v["signed_manifest"]
			delete(v, "signed_manifest")
		}},
		{"extra-signed-manifest-alias", func(v map[string]json.RawMessage) { v["Signed_Manifest"] = v["signed_manifest"] }},
		{"numeric-payload-array", func(v map[string]json.RawMessage) {
			numbers := []uint64{}
			for _, b := range payload {
				numbers = append(numbers, uint64(b))
			}
			v["payload"] = encodedV2(t, numbers)
		}},
		{"alternate-signature", func(v map[string]json.RawMessage) {
			var envelope map[string]json.RawMessage
			if e := json.Unmarshal(v["signed_manifest"], &envelope); e != nil {
				t.Fatal(e)
			}
			envelope["Signature"] = envelope["signature"]
			delete(envelope, "signature")
			v["signed_manifest"] = encodedV2(t, envelope)
		}},
		{"numeric-signature-array", func(v map[string]json.RawMessage) {
			var envelope map[string]json.RawMessage
			if e := json.Unmarshal(v["signed_manifest"], &envelope); e != nil {
				t.Fatal(e)
			}
			numbers := []uint64{}
			for _, b := range signed.Signature {
				numbers = append(numbers, uint64(b))
			}
			envelope["signature"] = encodedV2(t, numbers)
			v["signed_manifest"] = encodedV2(t, envelope)
		}},
	}
	for index, item := range cases {
		t.Run(item.name, func(t *testing.T) {
			var changed map[string]json.RawMessage
			if e := json.Unmarshal(base, &changed); e != nil {
				t.Fatal(e)
			}
			item.change(changed)
			result := request("PUT", path+"/artifacts/"+digest, fmt.Sprintf("bad-wire-%d", index), encodedV2(t, changed))
			if result.Code != http.StatusBadRequest {
				t.Fatalf("expected400, got%d: %s", result.Code, result.Body.String())
			}
		})
	}
	if absent := request("GET", path+"/artifacts/"+digest, "", nil); absent.Code != http.StatusNotFound {
		t.Fatalf("rejected wire persisted an artifact: %d %s", absent.Code, absent.Body.String())
	}
	audit := request("GET", path+"/audit", "", nil)
	if audit.Code != 200 {
		t.Fatal(audit.Body.String())
	}
	var page struct {
		Events []release.Event `json:"events"`
		Next   uint64          `json:"next"`
	}
	if e := protocol.DecodeJSON(audit.Body.Bytes(), &page); e != nil || len(page.Events) != 0 || page.Next != 0 {
		t.Fatal("rejected wire mutated audit/domain state", e)
	}
	accepted := request("PUT", path+"/artifacts/"+digest, "canonical-wire", base)
	if accepted.Code != http.StatusCreated {
		t.Fatalf("canonical upload changed: %d %s", accepted.Code, accepted.Body.String())
	}
	audit = request("GET", path+"/audit", "", nil)
	if e := protocol.DecodeJSON(audit.Body.Bytes(), &page); e != nil || len(page.Events) != 1 {
		t.Fatal("canonical upload not persisted exactly once", e)
	}
}
