//go:build ignore

// Original TEST ONLY strict-wire corpus. Public reproducible seeds are never
// product signing authority. Existing signed-release-v1.json is not modified.
// Run from services: go run ./protocol/testdata/generate-v1-wire.go --test-fixtures-only --repository ..
package main

import (
	"bytes"
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"mixer/services/protocol"
)

func must(e error) {
	if e != nil {
		panic(e)
	}
}
func encoded(v any) []byte { b, e := json.Marshal(v); must(e); return b }
func object(v any) map[string]any {
	var m map[string]any
	d := json.NewDecoder(bytes.NewReader(encoded(v)))
	d.UseNumber()
	must(d.Decode(&m))
	return m
}
func key(role string) ed25519.PrivateKey {
	seed := sha256.Sum256([]byte("Mixer public TEST ONLY legacy v1 strict-wire corpus / " + role))
	return ed25519.NewKeyFromSeed(seed[:])
}

type document struct {
	Name     string `json:"name"`
	Kind     string `json:"kind"`
	Accepted bool   `json:"accepted"`
	JSON     string `json:"json"`
}

func main() {
	only := flag.Bool("test-fixtures-only", false, "acknowledge public test-only roots")
	repository := flag.String("repository", "", "repository directory")
	flag.Parse()
	if !*only || *repository == "" {
		panic("--test-fixtures-only and --repository required")
	}
	scope := protocol.Scope{Organization: "wire-org", Project: "wire-project", App: "fieldlog", Environment: "development", Platform: "ios"}
	host := protocol.Host{Scope: scope, Runtime: protocol.Hash([]byte("TEST ONLY legacy wire runtime; not an installed fingerprint attestation")), Protocol: 1, GuestABI: 1, UISchema: 1,
		CapabilityHashes: map[string]string{"SCHEMA": protocol.Hash([]byte("upper")), "Schema": protocol.Hash([]byte("title")), "schema": protocol.Hash([]byte("lower")), "state": protocol.Hash([]byte("state"))},
		StateVersion:     0, MaxPayloadBytes: protocol.MaxPayloadBytes, Limits: protocol.Limits{MemoryBytes: 67108864, Fuel: 1000000, StartupMilliseconds: 5000}}
	artifactKey, assignmentKey := key("artifact"), key("assignment")
	roots := []protocol.Root{{KeyID: "wire-test-artifact", PublicKey: artifactKey.Public().(ed25519.PublicKey), Scope: scope, Artifact: true}, {KeyID: "wire-test-assignment", PublicKey: assignmentKey.Public().(ed25519.PublicKey), Scope: scope, Assignment: true}}
	payload := []byte("TEST ONLY v1 strict-wire fixture; not executable Wasm")
	m := protocol.Manifest{Schema: 1, Scope: scope, ReleaseID: "wire-test-release", SourceCommit: strings.Repeat("a", 40), ProvenanceID: "wire-test-provenance", Runtime: host.Runtime, Protocol: 1, GuestABI: 1, UISchema: 1, CapabilityHashes: host.CapabilityHashes, StateMin: 0, StateMax: 0,
		PayloadSHA256: protocol.Hash(payload), CompressedBytes: uint64(len(payload)), ExpandedBytes: uint64(len(payload)), Compression: "none", AssetHashes: map[string]string{}, SourceMapSHA256: protocol.Hash(nil), Limits: protocol.Limits{MemoryBytes: 1048576, Fuel: 1000, StartupMilliseconds: 1000}, KeyID: roots[0].KeyID, CreatedAtUnix: 1792627200}
	signed, e := protocol.SignManifest(m, artifactKey)
	must(e)
	digest, e := protocol.ManifestDigest(m)
	must(e)
	a := protocol.Assignment{Schema: 1, Scope: scope, Channel: "beta", Cohort: "sha256-v1", RolloutBasisPoints: 10000, Sequence: 7, ReleaseID: m.ReleaseID, ArtifactSHA256: digest, Runtime: host.Runtime, KeyID: roots[1].KeyID, CreatedAtUnix: m.CreatedAtUnix}
	assignment, e := protocol.SignAssignment(a, assignmentKey)
	must(e)
	documents := []document{}
	add := func(kind, name string, accepted bool, base any, mutate func(map[string]any)) {
		v := object(base)
		mutate(v)
		documents = append(documents, document{name, kind, accepted, string(encoded(v))})
	}
	unchanged := func(map[string]any) {}
	add("manifest", "canonical-dynamic-capability-map-case-keys", true, signed, unchanged)
	add("assignment", "canonical-assignment", true, assignment, unchanged)
	add("host", "canonical-host", true, host, unchanged)
	add("root", "canonical-root", true, roots[0], unchanged)
	// Every fixed field, including zero/false values, is required. Case aliases
	// are forbidden only at these model positions, never inside dynamic maps.
	modelCases := func(kind, label string, base any, path []string) {
		prototype := object(base)
		target := prototype
		for _, name := range path {
			target = target[name].(map[string]any)
		}
		names := []string{}
		for name := range target {
			names = append(names, name)
		}
		sort.Strings(names)
		for _, name := range names {
			for _, mode := range []string{"missing", "case", "alias"} {
				add(kind, label+"-"+mode+"-"+name, false, base, func(v map[string]any) {
					for _, component := range path {
						v = v[component].(map[string]any)
					}
					value := v[name]
					switch mode {
					case "missing":
						delete(v, name)
					case "case":
						v[strings.ToUpper(name)] = value
						delete(v, name)
					case "alias":
						v[strings.ToUpper(name)] = value
					}
				})
			}
		}
	}
	modelCases("manifest", "envelope", signed, nil)
	modelCases("manifest", "manifest", signed, []string{"manifest"})
	modelCases("manifest", "manifest-scope", signed, []string{"manifest", "scope"})
	modelCases("manifest", "manifest-limits", signed, []string{"manifest", "limits"})
	modelCases("assignment", "assignment-envelope", assignment, nil)
	modelCases("assignment", "assignment", assignment, []string{"assignment"})
	modelCases("assignment", "assignment-scope", assignment, []string{"assignment", "scope"})
	modelCases("host", "host", host, nil)
	modelCases("host", "host-scope", host, []string{"scope"})
	modelCases("host", "host-limits", host, []string{"limits"})
	modelCases("root", "root", roots[0], nil)
	modelCases("root", "root-scope", roots[0], []string{"scope"})
	add("manifest", "conflicting-SCHEMA-zero-before-signed-one", false, signed, func(v map[string]any) { v["manifest"].(map[string]any)["SCHEMA"] = uint64(0) })
	add("host", "host-conflicting-state-version-alias", false, host, func(v map[string]any) { v["STATE_VERSION"] = uint64(1) })
	add("root", "root-conflicting-revoked-alias", false, roots[0], func(v map[string]any) { v["REVOKED"] = true })
	malformedBytes := func(kind, label, field string, base any) {
		original := object(base)[field].(string)
		data, e := base64.StdEncoding.DecodeString(original)
		must(e)
		numbers := []uint64{}
		for _, b := range data {
			numbers = append(numbers, uint64(b))
		}
		alphabet := "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
		bits := []byte(original)
		index := len(strings.TrimRight(original, "=")) - 1
		bits[index] = alphabet[strings.IndexByte(alphabet, bits[index])+1]
		for _, item := range []struct {
			name  string
			value any
		}{{"numeric-array", numbers}, {"CRLF", original[:12] + "\r\n" + original[12:]}, {"nonzero-pad-bits", string(bits)}, {"missing-padding", strings.TrimRight(original, "=")}, {"short", base64.StdEncoding.EncodeToString(data[:len(data)-1])}, {"integer", uint64(1)}} {
			add(kind, label+"-"+item.name, false, base, func(v map[string]any) { v[field] = item.value })
		}
	}
	malformedBytes("manifest", "signature", "signature", signed)
	malformedBytes("assignment", "assignment-signature", "signature", assignment)
	malformedBytes("root", "public-key", "public_key", roots[0])
	// JSON escape spelling is inspection transport. A single escaped field name
	// must retain its decoded identity; duplicate decoded spellings still reject.
	canonical := string(encoded(signed))
	escaped := strings.Replace(canonical, `"schema":1`, `"\u0073chema":1`, 1)
	documents = append(documents, document{"single-escaped-model-key", "manifest", true, escaped})
	duplicate := strings.Replace(canonical, `"schema":1`, `"schema":1,"\u0073chema":1`, 1)
	documents = append(documents, document{"escaped-duplicate-model-key", "manifest", false, duplicate})
	escapedDynamic := strings.Replace(canonical, `"SCHEMA":`, `"\u0053CHEMA":`, 1)
	documents = append(documents, document{"single-escaped-dynamic-map-key", "manifest", true, escapedDynamic})
	for _, item := range []struct{ name, old, replacement string }{{"unsigned-fraction", `"schema":1`, `"schema":1.0`}, {"unsigned-exponent", `"schema":1`, `"schema":1e0`}, {"unsigned-negative-zero", `"state_min":0`, `"state_min":-0`}, {"unsigned-overflow", `"state_min":0`, `"state_min":18446744073709551616`}} {
		documents = append(documents, document{item.name, "manifest", false, strings.Replace(canonical, item.old, item.replacement, 1)})
	}
	documents = append(documents, document{"trailing-document", "manifest", false, canonical + " {}"})
	// A fresh assignment at UInt64's boundary is valid; no float conversion may
	// change its signed numeric value or replay comparison.
	a.Sequence = ^uint64(0)
	maximum, e := protocol.SignAssignment(a, assignmentKey)
	must(e)
	add("assignment", "maximum-uint64-sequence", true, maximum, unchanged)
	b, e := protocol.CanonicalCBOR(m)
	must(e)
	ab, e := protocol.CanonicalCBOR(assignment.Assignment)
	must(e)
	corpus := map[string]any{"test_only": true, "description": "Originally authored strict v1 transport corpus. Public TEST ONLY roots; payload not executable. Canonical v1 domains/values remain unchanged. Model fields are closed; capability map keys remain dynamic and case-sensitive.", "host": host, "roots": roots, "payload": payload, "signed_manifest": signed, "signed_assignment": assignment, "verification_time_unix": uint64(1792627300), "installation": "wire-test-installation", "last_sequence": uint64(6), "artifact_sha256": digest, "manifest_cbor_hex": hex.EncodeToString(b), "assignment_cbor_hex": hex.EncodeToString(ab), "documents": documents}
	data, e := json.MarshalIndent(corpus, "", "  ")
	must(e)
	for _, relative := range []string{"services/protocol/testdata", "updates/Tests/MixerUpdatesTests/Fixtures"} {
		must(os.WriteFile(filepath.Join(*repository, relative, "legacy-v1-wire-cases.json"), append(data, '\n'), 0644))
	}
	fmt.Printf("TEST ONLY v1 wire corpus %s; %d documents\n", digest, len(documents))
}
