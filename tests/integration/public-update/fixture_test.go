package publicupdatefixture

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"testing"

	"mixer/services/internal/testutil"
	"mixer/services/protocol"
	"mixer/services/release"
)

func TestSignInputs(t *testing.T) {
	dir := os.Getenv("FIXTURE_DIRECTORY")
	f := testutil.New(t).Protocol3()
	write := func(name string, data []byte) {
		t.Helper()
		if err := os.WriteFile(filepath.Join(dir, name), data, 0600); err != nil {
			t.Fatal(err)
		}
	}
	document := func(name string, object any) {
		t.Helper()
		data, err := json.Marshal(object)
		if err != nil {
			t.Fatal(err)
		}
		write(name, append(data, '\n'))
	}
	const channel = "production"
	sign := func(manifest protocol.ManifestV3, name string, sequence, rollout uint64) protocol.SignedAssignmentV3 {
		t.Helper()
		assignment := f.AssignmentV3(t, manifest, sequence, rollout).Assignment
		assignment.Channel = channel
		signed, err := protocol.SignAssignmentV3(assignment, f.AssignmentKey)
		if err != nil {
			t.Fatal(err)
		}
		document(name+".json", signed)
		return signed
	}
	candidate := func(name string) protocol.SignedManifestV3 {
		t.Helper()
		if err := os.Mkdir(filepath.Join(dir, name), 0700); err != nil {
			t.Fatal(err)
		}
		payload := []byte("TEST ONLY local release payload " + name)
		manifest := f.ManifestV3(t, payload, name)
		document(name+"/signed-manifest.json", manifest)
		write(name+"/payload.wasm", payload)
		return manifest
	}
	first, second := candidate("first"), candidate("second")
	published := sign(first.Manifest, "publish-first", 1, 500)
	sign(first.Manifest, "promote", 2, 2500)
	sign(first.Manifest, "shrink", 3, 500)
	replaced := sign(second.Manifest, "publish-second", 3, 10000)
	sign(first.Manifest, "rollback", 4, 10000)
	installation := map[string]string{}
	for i := 0; i < 1000 && len(installation) < 3; i++ {
		id := fmt.Sprintf("install-%d", i)
		bucket, err := protocol.Cohort(protocol.Assignment(published.Assignment), id)
		if err != nil {
			t.Fatal(err)
		}
		label := "outside"
		if bucket < 500 {
			label = "early"
		} else if bucket < 2500 {
			label = "expansion"
		}
		if installation[label] == "" {
			installation[label] = id
		}
	}
	if len(installation) != 3 {
		t.Fatal("missing cohort fixture")
	}
	scope := f.Host.Scope
	document("service.json", release.Config{
		DeveloperMode: true,
		Listen: os.Getenv("FIXTURE_ADDRESS"),
		DataDirectory: filepath.Join(dir, "store"),
		Roots: f.Roots, Hosts: []protocol.Host{f.Host},
		Tokens: []release.Token{
			{SHA256: protocol.Hash([]byte(os.Getenv("FIXTURE_PUBLISHER"))), Role: "publisher", Organization: scope.Organization, Project: scope.Project, Actor: "local-publisher"},
			{SHA256: protocol.Hash([]byte(os.Getenv("FIXTURE_FOREIGN"))), Role: "publisher", Organization: scope.Organization, Project: "foreign-project", Actor: "foreign-publisher"},
			{SHA256: protocol.Hash([]byte(os.Getenv("FIXTURE_READER"))), Role: "reader", Organization: scope.Organization, Project: scope.Project, Actor: "local-reader"},
		},
	})
	document("coordinates.json", map[string]any{
		"scope": scope, "runtime": f.Host.Runtime, "channel": channel, "installations": installation,
		"first": published.Assignment.ArtifactSHA256, "second": replaced.Assignment.ArtifactSHA256,
	})
}
