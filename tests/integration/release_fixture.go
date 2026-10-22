// Original integration fixture. These disposable keys never enter a real app.
package main

import (
	"crypto/ed25519"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"mixer/services/protocol"
	"mixer/services/release"
)

func main() {
	if len(os.Args) != 3 {
		panic("usage: release_fixture OUTPUT_DIRECTORY LOOPBACK_ADDRESS")
	}
	directory, address := os.Args[1], os.Args[2]
	if err := os.MkdirAll(directory, 0700); err != nil {
		panic(err)
	}
	tokenBytes := make([]byte, 32)
	if _, err := rand.Read(tokenBytes); err != nil {
		panic(err)
	}
	token := hex.EncodeToString(tokenBytes)
	write(directory, "admin.token", []byte(token))
	cfg := release.Config{DeveloperMode: true, Listen: address, DataDirectory: filepath.Join(directory, "service-data"), Tokens: []release.Token{{SHA256: protocol.Hash([]byte(token)), Role: "publisher", Organization: "integration", Project: "fieldlog", Actor: "integration-test"}}}
	payload := completionModule()
	write(directory, "payload.wasm", payload)
	for _, platform := range []string{"ios", "android"} {
		scope := protocol.Scope{Organization: "integration", Project: "fieldlog", App: "fieldlog-fixture", Environment: "test", Platform: platform}
		pub, key, err := ed25519.GenerateKey(rand.Reader)
		if err != nil {
			panic(err)
		}
		root := protocol.Root{KeyID: "test-" + platform, PublicKey: pub, Scope: scope, Artifact: true, Assignment: true}
		host := protocol.Host{Scope: scope, Runtime: protocol.Hash([]byte("mixer-integration-runtime-" + platform)), Protocol: 1, GuestABI: 1, UISchema: 1, CapabilityHashes: map[string]string{}, StateVersion: 1, MaxPayloadBytes: 1 << 20, Limits: protocol.Limits{MemoryBytes: 1 << 20, Fuel: 10000, StartupMilliseconds: 1000}}
		manifest := protocol.Manifest{Schema: 1, Scope: scope, ReleaseID: "completion-fix-1", SourceCommit: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", ProvenanceID: "original-integer-fixture", Runtime: host.Runtime, Protocol: 1, GuestABI: 1, UISchema: 1, CapabilityHashes: map[string]string{}, StateMin: 1, StateMax: 1, PayloadSHA256: protocol.Hash(payload), CompressedBytes: uint64(len(payload)), ExpandedBytes: uint64(len(payload)), Compression: "none", AssetHashes: map[string]string{}, SourceMapSHA256: protocol.Hash(nil), Limits: host.Limits, KeyID: root.KeyID, CreatedAtUnix: 1792627200}
		signed, err := protocol.SignManifest(manifest, key)
		if err != nil {
			panic(err)
		}
		digest, err := protocol.ManifestDigest(manifest)
		if err != nil {
			panic(err)
		}
		assignment := protocol.Assignment{Schema: 1, Scope: scope, Channel: "internal", Cohort: "sha256-v1", RolloutBasisPoints: 10000, Sequence: 1, ReleaseID: manifest.ReleaseID, ArtifactSHA256: digest, Runtime: host.Runtime, KeyID: root.KeyID, CreatedAtUnix: 1792627200}
		signedAssignment, err := protocol.SignAssignment(assignment, key)
		if err != nil {
			panic(err)
		}
		jsonFile(directory, platform+"-manifest.json", signed)
		jsonFile(directory, platform+"-assignment.json", signedAssignment)
		jsonFile(directory, platform+"-host.json", host)
		jsonFile(directory, platform+"-roots.json", []protocol.Root{root})
		jsonFile(directory, platform+"-upload.json", map[string]any{"signed_manifest": signed, "payload": payload})
		jsonFile(directory, platform+"-publish.json", map[string]any{"signed_assignment": signedAssignment})
		write(directory, platform+"-digest", []byte(digest))
		cfg.Roots = append(cfg.Roots, root)
		cfg.Hosts = append(cfg.Hosts, host)
	}
	jsonFile(directory, "service.json", cfg)
	fmt.Println("Prepared ephemeral integration fixtures; private keys discarded; not Swift or device qualification.")
}
func write(root, name string, bytes []byte) {
	if err := os.WriteFile(filepath.Join(root, name), bytes, 0600); err != nil {
		panic(err)
	}
}
func jsonFile(root, name string, value any) {
	b, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		panic(err)
	}
	write(root, name, b)
}
func leb(value uint32) []byte {
	var b []byte
	for {
		v := byte(value & 127)
		value >>= 7
		if value != 0 {
			v |= 128
		}
		b = append(b, v)
		if value == 0 {
			return b
		}
	}
}
func section(module []byte, id byte, body []byte) []byte {
	module = append(module, id)
	module = append(module, leb(uint32(len(body)))...)
	return append(module, body...)
}
func completionModule() []byte {
	m := []byte{0, 97, 115, 109, 1, 0, 0, 0}
	m = section(m, 1, []byte{1, 0x60, 2, 0x7f, 0x7f, 1, 0x7f})
	m = section(m, 3, []byte{1, 0})
	export := append([]byte{1, 10}, []byte("completion")...)
	export = append(export, 0, 0)
	m = section(m, 7, export)
	// (completed,total) -> total==0 ? 0 : completed*10000/total.
	body := []byte{0, 0x20, 1, 0x45, 0x04, 0x7f, 0x41, 0, 0x05, 0x20, 0, 0x41, 0x90, 0xce, 0x00, 0x6c, 0x20, 1, 0x6e, 0x0b, 0x0b}
	code := append([]byte{1}, leb(uint32(len(body)))...)
	code = append(code, body...)
	return section(m, 10, code)
}
