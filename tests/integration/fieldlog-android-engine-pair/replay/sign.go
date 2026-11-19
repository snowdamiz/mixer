package main

import (
	"crypto/ed25519"
	"crypto/rand"
	"encoding/json"
	"maps"
	"os"
	"path/filepath"
	"time"

	"mixer/services/protocol"
)

const keyID = "fieldlog-engine-pair-rebuild-local"

type release struct {
	Digest     string                      `json:"digest"`
	Manifest   protocol.SignedManifestV3   `json:"manifest"`
	Assignment protocol.SignedAssignmentV3 `json:"assignment"`
}

func must[T any](value T, err error) T {
	if err != nil {
		panic(err)
	}
	return value
}

func load[T any](path string) T {
	var value T
	if err := protocol.DecodeJSON(must(os.ReadFile(path)), &value); err != nil {
		panic(err)
	}
	return value
}

func main() {
	dir := os.Args[2]
	keyPath := filepath.Join(dir, "ota-private-seed")
	if os.Args[1] == "root" {
		public, private, err := ed25519.GenerateKey(rand.Reader)
		if err != nil {
			panic(err)
		}
		file := must(os.OpenFile(keyPath, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600))
		must(file.Write(private.Seed()))
		if err := file.Close(); err != nil {
			panic(err)
		}
		template := load[protocol.ManifestV3](filepath.Join(dir, "old.original.manifest.json"))
		root := protocol.Root{KeyID: keyID, Scope: template.Scope, PublicKey: public,
			Artifact: true, Assignment: true, NotBeforeUnix: 1}
		must(os.Stdout.Write(must(json.Marshal([]protocol.Root{root}))))
		return
	}
	if os.Args[1] != "issue" {
		panic("expected root or issue")
	}

	private := ed25519.NewKeyFromSeed(must(os.ReadFile(keyPath)))
	old := load[protocol.Host](filepath.Join(dir, "old.host.json"))
	next := load[protocol.Host](filepath.Join(dir, "new.host.json"))
	if old.Scope != next.Scope || old.Runtime == next.Runtime ||
		old.Scope.Environment != "development" || old.Scope.Platform != "android" {
		panic("expected two Android runtimes in one development scope")
	}
	now := uint64(time.Now().Unix())
	issue := func(host protocol.Host, label string, sequence uint64) release {
		manifest := load[protocol.ManifestV3](filepath.Join(dir, label+".original.manifest.json"))
		payload := must(os.ReadFile(filepath.Join(dir, label+".wasm")))
		if manifest.Scope != host.Scope || manifest.Protocol != host.Protocol || manifest.GuestABI != host.GuestABI ||
			manifest.UISchema != host.UISchema || !maps.Equal(manifest.CapabilityHashes, host.CapabilityHashes) ||
			protocol.Hash(payload) != manifest.PayloadSHA256 {
			panic("guest or scope differs from the admitted template")
		}
		manifest.Runtime, manifest.KeyID, manifest.CreatedAtUnix = host.Runtime, keyID, now
		signed := must(protocol.SignManifestV3(manifest, private))
		digest := must(protocol.ManifestDigestV3(manifest))
		assignment := must(protocol.SignAssignmentV3(protocol.AssignmentV3{
			Schema: 3, Scope: host.Scope, Channel: "beta", Cohort: "sha256-v1",
			RolloutBasisPoints: 10000, Sequence: sequence, ReleaseID: manifest.ReleaseID,
			ArtifactSHA256: digest, Runtime: host.Runtime, KeyID: keyID, CreatedAtUnix: now,
		}, private))
		return release{digest, signed, assignment}
	}
	oldIssue, newIssue := issue(old, "old", 7), issue(next, "new", 1)
	transplant := func(issued release, runtime string, sequence uint64) protocol.SignedAssignmentV3 {
		cross := issued.Assignment.Assignment
		cross.Runtime, cross.Sequence = runtime, sequence
		return must(protocol.SignAssignmentV3(cross, private))
	}
	installation := "a4d88fe1-13fd-4b82-bc7a-3376c2fa00ea"
	bucket := must(protocol.Cohort(protocol.Assignment(oldIssue.Assignment.Assignment), installation))
	if bucket != must(protocol.Cohort(protocol.Assignment(newIssue.Assignment.Assignment), installation)) {
		panic("runtime change altered stable installation bucket")
	}
	bytes := must(json.Marshal(map[string]any{
		"old": oldIssue, "new": newIssue,
		"new_into_old": transplant(newIssue, old.Runtime, 8),
		"old_into_new": transplant(oldIssue, next.Runtime, 2),
		"installation": installation, "bucket": bucket, "now": now,
	}))
	must(os.Stdout.Write(bytes))
}
