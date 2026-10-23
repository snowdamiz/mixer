// Original external public-API integration; keys and bearer are TEST ONLY.
package main

import (
	"bytes"
	"crypto/ed25519"
	"encoding/json"
	"fmt"
	"io"
	"mixer/services/protocol"
	"mixer/services/release"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

func must(e error) {
	if e != nil {
		panic(e)
	}
}
func encode(v any) []byte { b, e := json.Marshal(v); must(e); return b }
func main() {
	out, binary := os.Args[1], os.Args[2]
	must(os.MkdirAll(out, 0700))
	data, e := os.MkdirTemp("", "mixer-root-service3-")
	must(e)
	defer os.RemoveAll(data)
	scope := protocol.Scope{Organization: "root-review", Project: "service", App: "probe", Environment: "test", Platform: "ios"}
	key := ed25519.NewKeyFromSeed(bytes.Repeat([]byte{71}, 32))
	roots := []protocol.Root{{KeyID: "test-only", PublicKey: key.Public().(ed25519.PublicKey), Scope: scope, Artifact: true, Assignment: true}}
	host := protocol.Host{Scope: scope, Runtime: protocol.Hash([]byte("TEST ONLY independent service3 host")), Protocol: 3, GuestABI: 2, UISchema: 1, CapabilityHashes: map[string]string{protocol.StorageGrantID: protocol.StorageGrantSHA256}, StateVersion: 1, MaxPayloadBytes: 4194304, Limits: protocol.Limits{MemoryBytes: 4194304, Fuel: 1000000, StartupMilliseconds: 1000}}
	payload := []byte("TEST ONLY original public HTTP payload, not executable")
	manifest := protocol.ManifestV3{Schema: 3, Scope: scope, ReleaseID: "root-release", SourceCommit: strings.Repeat("b", 40), ProvenanceID: "TEST-ONLY-root", Runtime: host.Runtime, Protocol: 3, GuestABI: 2, UISchema: 1, CapabilityHashes: host.CapabilityHashes, CapabilityGrants: protocol.CapabilityGrants{Schema: 1, SchemaSHA256: protocol.GrantSchemaSHA256, Entries: []protocol.CapabilityGrant{{CapabilityID: protocol.StorageGrantID, SchemaSHA256: protocol.StorageGrantSHA256, Permissions: []string{"storage.appPrivate"}, Origins: []string{}, Methods: []string{}, Namespaces: []string{"Drafts", "drafts"}}}}, StateMin: 1, StateMax: 1, PayloadSHA256: protocol.Hash(payload), CompressedBytes: uint64(len(payload)), ExpandedBytes: uint64(len(payload)), Compression: "none", AssetHashes: map[string]string{}, SourceMapSHA256: protocol.Hash(nil), Limits: protocol.Limits{MemoryBytes: 1, Fuel: 777, StartupMilliseconds: 1000}, KeyID: "test-only", CreatedAtUnix: 100}
	signed, e := protocol.SignManifestV3(manifest, key)
	must(e)
	digest, e := protocol.ManifestDigestV3(manifest)
	must(e)
	assigned, e := protocol.SignAssignmentV3(protocol.AssignmentV3{Schema: 3, Scope: scope, Channel: "beta", Cohort: "sha256-v1", RolloutBasisPoints: 10000, Sequence: 7, ReleaseID: manifest.ReleaseID, ArtifactSHA256: digest, Runtime: host.Runtime, KeyID: "test-only", CreatedAtUnix: 100}, key)
	must(e)
	cfg := release.Config{DeveloperMode: true, Listen: "127.0.0.1:0", DataDirectory: data, Hosts: []protocol.Host{host}, Roots: roots, Tokens: []release.Token{{SHA256: protocol.Hash([]byte("TEST ONLY root")), Role: "publisher", Organization: scope.Organization, Project: scope.Project, Actor: "root-test"}}}
	service, e := release.New(cfg)
	must(e)
	server := httptest.NewServer(service)
	defer func() { server.Close(); service.Close() }()
	checks := 0
	request := func(method, path, id string, body []byte, want int) []byte {
		req, e := http.NewRequest(method, server.URL+path, bytes.NewReader(body))
		must(e)
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("Authorization", "Bearer TEST ONLY root")
		req.Header.Set("Idempotency-Key", id)
		response, e := server.Client().Do(req)
		must(e)
		b, e := io.ReadAll(io.LimitReader(response.Body, 7*1024*1024))
		must(e)
		must(response.Body.Close())
		if response.StatusCode != want {
			panic(fmt.Sprintf("%s status%d wanted%d: %s", path, response.StatusCode, want, b))
		}
		checks++
		return b
	}
	prefix := "/v3/orgs/root-review/projects/service"
	upload := encode(release.ArtifactV3{SignedManifest: signed, Payload: payload})
	request("PUT", prefix+"/artifacts/"+digest, "upload", upload, 201)
	request("GET", "/v3/artifacts/"+digest+"?organization=root-review&project=service", "", nil, 404)
	request("POST", prefix+"/releases/validate", "null", []byte(`{"artifact_sha256":null}`), 400)
	request("POST", prefix+"/releases/validate", "duplicate", []byte(`{"artifact_sha256":"`+digest+`","artifact_sha256":"`+digest+`"}`), 400)
	request("POST", prefix+"/releases/validate", "too-large", bytes.Repeat([]byte{' '}, 128*1024+1), 413)
	request("POST", prefix+"/releases/validate", "validate", encode(map[string]string{"artifact_sha256": digest}), 200)
	publish := encode(map[string]any{"signed_assignment": assigned})
	first := request("POST", prefix+"/channels/beta/publish", "publish", publish, 200)
	request("POST", prefix+"/channels/beta/publish", "replay", publish, 409)
	for _, v := range []string{"1", "2"} {
		request("GET", "/v"+v+"/artifacts/"+digest+"?organization=root-review&project=service", "", nil, 404)
	}
	fixture := filepath.Join(out, "fixture.json")
	must(os.WriteFile(fixture, encode(map[string]any{"host": host, "roots": roots, "artifact": digest, "payload": payload}), 0600))
	run := func(name string) {
		cmd := exec.Command(binary, server.URL, fixture)
		b, e := cmd.CombinedOutput()
		must(os.WriteFile(filepath.Join(out, name+".log"), b, 0600))
		if e != nil {
			panic(string(b))
		}
		fmt.Print(string(b))
	}
	run("swift-before-reopen")
	server.Close()
	must(service.Close())
	service, e = release.New(cfg)
	must(e)
	server = httptest.NewServer(service)
	again := request("POST", prefix+"/channels/beta/publish", "publish", publish, 200)
	if !bytes.Equal(first, again) {
		panic("idempotent response changed")
	}
	run("swift-after-reopen")
	must(os.WriteFile(filepath.Join(out, "artifact.json"), request("GET", "/v3/artifacts/"+digest+"?organization=root-review&project=service", "", nil, 200), 0600))
	fmt.Printf("PASS %d independent TCP HTTP assertions plus two public Swift consumer runs; local temporary store removed on exit\n", checks)
}
