// Local-only fixture signer using the pinned release service's v3 protocol.
package main

import (
	"crypto/ed25519"
	"crypto/rand"
	"encoding/json"
	"fmt"
	"maps"
	"os"
	"path/filepath"
	"time"

	"mixer/services/protocol"
)

const keyID = "fieldlog-localized-development"

var scope = protocol.Scope{
	Organization: "mixer-local", Project: "fieldlog", App: "fieldlog",
	Environment: "development", Platform: "android",
}

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

func run(mode, dir string) any {
	seed := filepath.Join(dir, "ota-private-seed")
	switch mode {
	case "root":
		public, private, err := ed25519.GenerateKey(rand.Reader)
		if err != nil {
			panic(err)
		}
		file := must(os.OpenFile(seed, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600))
		must(file.Write(private.Seed()))
		if err := file.Close(); err != nil {
			panic(err)
		}
		return []protocol.Root{{KeyID: keyID, Scope: scope, PublicKey: public,
			Artifact: true, Assignment: true, NotBeforeUnix: 1}}
	case "issue":
		host := load[protocol.Host](filepath.Join(dir, "host.json"))
		if host.Scope != scope || host.Protocol != 3 || !protocol.ValidDigest(host.Runtime) {
			panic("expected one Android FieldLog development runtime")
		}
		private := ed25519.NewKeyFromSeed(must(os.ReadFile(seed)))
		now := uint64(time.Now().Unix())
		releases := make(map[string]release)
		for index, label := range []string{"baseline", "reviewed"} {
			manifest := load[protocol.ManifestV3](filepath.Join(dir, label+".manifest.json"))
			payload := must(os.ReadFile(filepath.Join(dir, label+".wasm")))
			if manifest.Scope != host.Scope || manifest.Protocol != host.Protocol ||
				manifest.GuestABI != host.GuestABI || manifest.UISchema != host.UISchema ||
				!maps.Equal(manifest.CapabilityHashes, host.CapabilityHashes) ||
				manifest.ReleaseID != "fieldlog-localized-"+label ||
				manifest.PayloadSHA256 != protocol.Hash(payload) ||
				manifest.CompressedBytes != uint64(len(payload)) || manifest.ExpandedBytes != uint64(len(payload)) {
				panic("manifest or payload differs from the localized release contract")
			}
			manifest.Runtime, manifest.KeyID, manifest.CreatedAtUnix = host.Runtime, keyID, now
			digest := must(protocol.ManifestDigestV3(manifest))
			assignment := protocol.AssignmentV3{
				Schema: 3, Scope: scope, Runtime: host.Runtime, Channel: "beta", Cohort: "sha256-v1",
				RolloutBasisPoints: 10000, Sequence: uint64(index + 1), ReleaseID: manifest.ReleaseID,
				ArtifactSHA256: digest, KeyID: keyID, CreatedAtUnix: now,
			}
			releases[label] = release{digest, must(protocol.SignManifestV3(manifest, private)),
				must(protocol.SignAssignmentV3(assignment, private))}
		}
		return releases
	default:
		panic(fmt.Sprintf("unknown signer mode %q", mode))
	}
}

func main() {
	if len(os.Args) != 3 {
		panic("expected root or issue and a private signing directory")
	}
	must(os.Stdout.Write(must(json.Marshal(run(os.Args[1], os.Args[2])))))
}
