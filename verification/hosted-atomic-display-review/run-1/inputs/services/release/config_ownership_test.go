package release_test

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"sync"
	"testing"

	"mixer/services/internal/testutil"
	"mixer/services/protocol"
	"mixer/services/release"
)

type ownedConfigFixture struct {
	cfg        release.Config
	base       string
	artifact   any
	digest     string
	assignment any
}

func configFixture(t *testing.T, version int) ownedConfigFixture {
	t.Helper()
	f := testutil.New(t)
	if version == 2 {
		f = f.Protocol2()
	} else if version == 3 {
		f = f.Protocol3()
	}
	payload := []byte("TEST ONLY configuration ownership payload")
	v := ownedConfigFixture{cfg: config(t, f), base: fmt.Sprintf("/v%d/orgs/org-a/projects/project-a", version)}
	var err error
	switch version {
	case 1:
		m := f.Manifest(t, payload, "owned-config")
		v.artifact = release.Artifact{SignedManifest: m, Payload: payload}
		v.digest, err = protocol.ManifestDigest(m.Manifest)
		v.assignment = f.Assignment(t, m.Manifest, 1, 10000)
	case 2:
		m := f.ManifestV2(t, payload, "owned-config")
		v.artifact = release.ArtifactV2{SignedManifest: m, Payload: payload}
		v.digest, err = protocol.ManifestDigestV2(m.Manifest)
		v.assignment = f.AssignmentV2(t, m.Manifest, 1, 10000)
	case 3:
		m := f.ManifestV3(t, payload, "owned-config")
		v.artifact = release.ArtifactV3{SignedManifest: m, Payload: payload}
		v.digest, err = protocol.ManifestDigestV3(m.Manifest)
		v.assignment = f.AssignmentV3(t, m.Manifest, 1, 10000)
	default:
		t.Fatal("unsupported fixture version")
	}
	if err != nil {
		t.Fatal(err)
	}
	return v
}

func configServer(t *testing.T, cfg release.Config) *release.Server {
	t.Helper()
	s, err := release.New(cfg)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		if err := s.Close(); err != nil {
			t.Error(err)
		}
	})
	return s
}

func (v ownedConfigFixture) upload(t *testing.T, s http.Handler, key string) {
	t.Helper()
	status(t, request(s, "PUT", v.base+"/artifacts/"+v.digest, key, "test publisher credential", v.artifact), 201)
}

func (v ownedConfigFixture) publish(t *testing.T, s http.Handler) {
	t.Helper()
	v.upload(t, s, "owned-upload")
	status(t, request(s, "POST", v.base+"/releases/validate", "owned-validate", "test publisher credential", map[string]string{"artifact_sha256": v.digest}), 200)
	status(t, request(s, "POST", v.base+"/channels/beta/publish", "owned-publish", "test publisher credential", map[string]any{"signed_assignment": v.assignment}), 200)
}

func TestConfigOwnershipPreservesTokenAuthority(t *testing.T) {
	for _, version := range []int{1, 2, 3} {
		t.Run(fmt.Sprintf("v%d", version), func(t *testing.T) {
			v := configFixture(t, version)
			s := configServer(t, v.cfg)
			v.cfg.Tokens[1].Role = "publisher"
			status(t, request(s, "PUT", v.base+"/artifacts/"+v.digest, "reader-cannot-write", "test reader credential", v.artifact), 403)
			v.cfg.Tokens[1].Organization = "org-b"
			v.cfg.Tokens[1].Project = "project-b"
			other := fmt.Sprintf("/v%d/orgs/org-b/projects/project-b/audit", version)
			status(t, request(s, "GET", other, "", "test reader credential", nil), 403)
			status(t, request(s, "GET", v.base+"/audit", "", "test reader credential", nil), 200)
			v.cfg.Tokens[0].Actor = "changed-actor"
			v.cfg.Tokens[0].SHA256 = protocol.Hash([]byte("TEST ONLY replacement credential"))
			status(t, request(s, "GET", v.base+"/audit", "", "TEST ONLY replacement credential", nil), 401)
			v.publish(t, s)
			w := request(s, "GET", v.base+"/audit", "", "test reader credential", nil)
			status(t, w, 200)
			var audit struct {
				Events []release.Event `json:"events"`
			}
			if err := json.Unmarshal(w.Body.Bytes(), &audit); err != nil {
				t.Fatal(err)
			}
			if len(audit.Events) != 3 {
				t.Fatalf("expected only original authorized workflow, got %d audit events", len(audit.Events))
			}
			for _, event := range audit.Events {
				if event.Actor != "test-publisher" || event.Organization != "org-a" || event.Project != "project-a" {
					t.Fatalf("caller mutation changed committed audit identity: %+v", event)
				}
			}
		})
	}
}

func TestConfigOwnershipPreservesTrustAndHostPolicy(t *testing.T) {
	mutations := []struct {
		name   string
		mutate func(*release.Config)
	}{
		{"artifact-key-bytes", func(c *release.Config) { c.Roots[0].PublicKey[0] ^= 1 }},
		{"assignment-key-bytes", func(c *release.Config) { c.Roots[1].PublicKey[0] ^= 1 }},
		{"root-record", func(c *release.Config) { c.Roots[0] = protocol.Root{} }},
		{"root-revocation", func(c *release.Config) { c.Roots[1].Revoked = true }},
		{"host-record", func(c *release.Config) { c.Hosts[0] = protocol.Host{} }},
		{"host-limit", func(c *release.Config) { c.Hosts[0].Limits.Fuel = 1 }},
		{"host-map-entry", func(c *release.Config) {
			for key := range c.Hosts[0].CapabilityHashes {
				c.Hosts[0].CapabilityHashes[key] = protocol.Hash([]byte("changed"))
			}
		}},
		{"host-map-delete", func(c *release.Config) { clear(c.Hosts[0].CapabilityHashes) }},
		{"host-map-replace", func(c *release.Config) { c.Hosts[0].CapabilityHashes = nil }},
	}
	for _, version := range []int{1, 2, 3} {
		for _, mutation := range mutations {
			t.Run(fmt.Sprintf("v%d/%s", version, mutation.name), func(t *testing.T) {
				v := configFixture(t, version)
				s := configServer(t, v.cfg)
				mutation.mutate(&v.cfg)
				v.publish(t, s)
			})
		}
	}
}

func TestConfigOwnershipRejectsCallerIntroducedSigningKey(t *testing.T) {
	f := testutil.New(t)
	cfg := config(t, f)
	s := configServer(t, cfg)
	other := testutil.New(t)
	copy(cfg.Roots[0].PublicKey, other.Roots[0].PublicKey)
	payload := []byte("TEST ONLY unconfigured signing authority")
	m := other.Manifest(t, payload, "caller-introduced-key")
	digest, err := protocol.ManifestDigest(m.Manifest)
	if err != nil {
		t.Fatal(err)
	}
	status(t, request(s, "PUT", base+"/artifacts/"+digest, "unconfigured-key", "test publisher credential", release.Artifact{SignedManifest: m, Payload: payload}), 422)
	good := upload(t, s, f, "original-key-still-valid")
	validate(t, s, good, "original-key-still-valid")
}

func TestConfigOwnershipConcurrentCallerMutation(t *testing.T) {
	v := configFixture(t, 3)
	s := configServer(t, v.cfg)
	stop := make(chan struct{})
	started := make(chan struct{})
	var writer sync.WaitGroup
	writer.Add(1)
	go func() {
		defer writer.Done()
		close(started)
		for i := 0; ; i++ {
			select {
			case <-stop:
				return
			default:
			}
			v.cfg.Tokens[0].Actor = fmt.Sprintf("caller-%d", i)
			v.cfg.Roots[0].PublicKey[0] ^= 1
			v.cfg.Roots[1].Revoked = !v.cfg.Roots[1].Revoked
			v.cfg.Hosts[0].Limits.Fuel = uint64(i)
			v.cfg.Hosts[0].CapabilityHashes[protocol.HTTPGrantID] = fmt.Sprintf("caller-%d", i)
		}
	}()
	defer func() { close(stop); writer.Wait() }()
	<-started
	for i := 0; i < 24; i++ {
		want := 200
		if i == 0 {
			want = 201
		}
		// Distinct idempotency keys force fresh authorization, trust and host
		// verification on each request instead of replaying a stored response.
		status(t, request(s, "PUT", v.base+"/artifacts/"+v.digest, fmt.Sprintf("upload-%d", i), "test publisher credential", v.artifact), want)
		status(t, request(s, "POST", v.base+"/releases/validate", fmt.Sprintf("validate-%d", i), "test publisher credential", map[string]string{"artifact_sha256": v.digest}), 200)
		status(t, request(s, "GET", v.base+"/audit", "", "test reader credential", nil), 200)
	}
}

func TestConfigOwnershipPreservesInvalidInputRejection(t *testing.T) {
	for _, mutate := range []func(*release.Config){
		func(c *release.Config) { c.DeveloperMode = false },
		func(c *release.Config) { c.Tokens = nil },
		func(c *release.Config) { c.Roots[0].PublicKey = nil },
		func(c *release.Config) { c.Hosts[0].CapabilityHashes = nil },
	} {
		v := configFixture(t, 3)
		mutate(&v.cfg)
		if s, err := release.New(v.cfg); err == nil {
			s.Close()
			t.Fatal("invalid input accepted after snapshot")
		}
		if _, err := os.Stat(filepath.Join(v.cfg.DataDirectory, "release.json")); !os.IsNotExist(err) {
			t.Fatalf("rejected construction reached durable storage: %v", err)
		}
	}
}
