//go:build ignore

// Original TEST ONLY fixture generator. These publicly reproducible test seeds
// are never signing authorities for an installed app or release service.
// Run from services: go run ./protocol/testdata/generate-v3.go --test-fixtures-only --repository ..
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
	"strconv"
	"strings"

	"mixer/services/protocol"
)

func must(err error) {
	if err != nil {
		panic(err)
	}
}
func testKey(role string) ed25519.PrivateKey {
	seed := sha256.Sum256([]byte("Mixer publicly reproducible TEST ONLY release-v3 fixture / " + role))
	return ed25519.NewKeyFromSeed(seed[:])
}
func convert(value any) any {
	switch v := value.(type) {
	case json.Number:
		n, e := strconv.ParseUint(string(v), 10, 64)
		must(e)
		return n
	case map[string]any:
		for key, item := range v {
			v[key] = convert(item)
		}
		return v
	case []any:
		for index, item := range v {
			v[index] = convert(item)
		}
		return v
	default:
		return value
	}
}
func value(raw []byte) any {
	d := json.NewDecoder(bytes.NewReader(raw))
	d.UseNumber()
	var v any
	must(d.Decode(&v))
	return convert(v)
}
func jsonBytes(v any) []byte { b, e := json.Marshal(v); must(e); return b }
func cbor(v any) []byte      { b, e := protocol.CanonicalCBOR(v); must(e); return b }
func write(path string, v any) {
	b, e := json.MarshalIndent(v, "", "  ")
	must(e)
	must(os.WriteFile(path, append(b, '\n'), 0644))
}

type ruleCase struct {
	Value    string `json:"value"`
	Accepted bool   `json:"accepted"`
}
type documentCase struct {
	Name     string `json:"name"`
	Accepted bool   `json:"accepted"`
	JSON     string `json:"signed_manifest_json"`
}

func main() {
	only := flag.Bool("test-fixtures-only", false, "acknowledge public test-only signing material")
	repository := flag.String("repository", "", "repository containing contracts, services and updates")
	flag.Parse()
	if !*only || *repository == "" {
		panic("explicit --test-fixtures-only and --repository required")
	}
	contract := value(mustRead(filepath.Join(*repository, "contracts/release-v3.json"))).(map[string]any)
	descriptor := contract["capability_grant_descriptor"]
	if protocol.Hash(cbor(descriptor)) != protocol.GrantSchemaSHA256 {
		panic("grant descriptor hash changed")
	}
	artifactKey, assignmentKey := testKey("artifact"), testKey("assignment")
	scope := protocol.Scope{Organization: "org-a", Project: "project-a", App: "fieldlog", Environment: "development", Platform: "ios"}
	host := protocol.Host{Scope: scope, Runtime: protocol.Hash([]byte("test-only-runtime-v3-including-installed-grants")), Protocol: 3, GuestABI: 2, UISchema: 1,
		CapabilityHashes: map[string]string{protocol.HTTPGrantID: protocol.HTTPGrantSHA256, protocol.StorageGrantID: protocol.StorageGrantSHA256}, StateVersion: 1, MaxPayloadBytes: protocol.MaxV3PayloadBytes,
		Limits: protocol.Limits{MemoryBytes: protocol.MaxV3MemoryBytes, Fuel: protocol.MaxV3Fuel, StartupMilliseconds: protocol.MaxV3StartupMilliseconds}}
	roots := []protocol.Root{
		{KeyID: "fixture-v3-artifact", PublicKey: artifactKey.Public().(ed25519.PublicKey), Scope: scope, Artifact: true},
		{KeyID: "fixture-v3-assignment", PublicKey: assignmentKey.Public().(ed25519.PublicKey), Scope: scope, Assignment: true},
	}
	payload := []byte("mixer independently authored signed grant protocol fixture v3")
	m := protocol.ManifestV3{Schema: 3, Scope: scope, ReleaseID: "fixture-release-v3", SourceCommit: strings.Repeat("a", 40), ProvenanceID: "fixture-provenance-v3", Runtime: host.Runtime, Protocol: 3, GuestABI: 2, UISchema: 1,
		CapabilityHashes: host.CapabilityHashes, CapabilityGrants: protocol.CapabilityGrants{Schema: 1, SchemaSHA256: protocol.GrantSchemaSHA256, Entries: []protocol.CapabilityGrant{
			{CapabilityID: protocol.HTTPGrantID, SchemaSHA256: protocol.HTTPGrantSHA256, Permissions: []string{"network.https"}, Origins: []string{"https://api.fieldlog.example", "https://uploads.fieldlog.example:8443"}, Methods: []string{"GET", "POST"}, Namespaces: []string{}},
			{CapabilityID: protocol.StorageGrantID, SchemaSHA256: protocol.StorageGrantSHA256, Permissions: []string{"storage.appPrivate"}, Origins: []string{}, Methods: []string{}, Namespaces: []string{"Drafts", "drafts", "outbox"}},
		}}, StateMin: 1, StateMax: 1, PayloadSHA256: protocol.Hash(payload), CompressedBytes: uint64(len(payload)), ExpandedBytes: uint64(len(payload)), Compression: "none", AssetHashes: map[string]string{}, SourceMapSHA256: protocol.Hash(nil), Limits: protocol.Limits{MemoryBytes: 1048576, Fuel: 1000, StartupMilliseconds: 1000}, KeyID: roots[0].KeyID, CreatedAtUnix: 1792627200}
	signed, e := protocol.SignManifestV3(m, artifactKey)
	must(e)
	digest, e := protocol.ManifestDigestV3(m)
	must(e)
	a := protocol.AssignmentV3{Schema: 3, Scope: scope, Channel: "beta", Cohort: "sha256-v1", RolloutBasisPoints: 10000, Sequence: 7, ReleaseID: m.ReleaseID, ArtifactSHA256: digest, Runtime: host.Runtime, KeyID: roots[1].KeyID, CreatedAtUnix: m.CreatedAtUnix}
	assignment, e := protocol.SignAssignmentV3(a, assignmentKey)
	must(e)
	bucket, e := protocol.Cohort(protocol.Assignment(a), "fixture-installation-v3")
	must(e)
	vector := map[string]any{"test_only": true, "description": "Original protocol-only vector with publicly reproducible TEST ONLY keys; never trust these keys in a product. Payload is a test string, not executable Wasm.", "signed_manifest": signed, "signed_assignment": assignment, "host": host, "roots": roots, "payload": payload, "artifact_sha256": digest, "manifest_cbor_hex": hex.EncodeToString(cbor(m)), "assignment_cbor_hex": hex.EncodeToString(cbor(a)), "manifest_message_hex": hex.EncodeToString(append([]byte(protocol.ArtifactDomainV3), cbor(m)...)), "assignment_message_hex": hex.EncodeToString(append([]byte(protocol.AssignmentDomainV3), cbor(a)...)), "grant_descriptor": descriptor, "grant_descriptor_cbor_hex": hex.EncodeToString(cbor(descriptor)), "installation": "fixture-installation-v3", "cohort_bucket": bucket, "last_sequence": uint64(6), "verification_time_unix": uint64(1792627300)}
	origins := []ruleCase{
		{"https://example.com", true}, {"https://localhost", true}, {"https://127.0.0.1", true}, {"https://a-b.example:1", true}, {"https://example.com:65535", true},
		{"https://" + strings.Repeat("a", 63) + ".example", true}, {"https://" + strings.Repeat("a", 63) + "." + strings.Repeat("b", 63) + "." + strings.Repeat("c", 63) + "." + strings.Repeat("d", 61), true},
		{"https://" + strings.Repeat("a", 64) + ".example", false}, {"https://" + strings.Repeat("a", 63) + "." + strings.Repeat("b", 63) + "." + strings.Repeat("c", 63) + "." + strings.Repeat("d", 62), false},
		{"", false}, {"http://example.com", false}, {"HTTPS://example.com", false}, {"https://Example.com", false}, {"https://example.com/", false}, {"https://example.com/path", false}, {"https://example.com?", false}, {"https://example.com#", false}, {"https://user@example.com", false}, {"https://example.com\\evil", false}, {"https://example.com.", false}, {"https://.example.com", false}, {"https://a..example", false}, {"https://-a.example", false}, {"https://a-.example", false}, {"https://a_b.example", false}, {"https://*.example", false}, {"https://é.example", false}, {"https://%65xample.com", false}, {"https://[::1]", false}, {"https://example.com:", false}, {"https://example.com:0", false}, {"https://example.com:443", false}, {"https://example.com:0443", false}, {"https://example.com:01", false}, {"https://example.com:+1", false}, {"https://example.com:-1", false}, {"https://example.com:65536", false}, {"https://example.com:1:2", false}, {"https://example.com\n", false},
	}
	namespaces := []ruleCase{{"Drafts", true}, {"drafts", true}, {"A_z-09", true}, {strings.Repeat("a", 64), true}, {"", false}, {strings.Repeat("a", 65), false}, {"drafts/one", false}, {"drafts.one", false}, {"..", false}, {"é", false}, {"e\u0301", false}, {"drafts\n", false}, {"drafts one", false}, {"drafts\\one", false}}
	cases := []documentCase{}
	base := jsonBytes(m)
	add := func(name string, accepted bool, mutate func(map[string]any), domain string) {
		manifest := value(base).(map[string]any)
		mutate(manifest)
		signature := ed25519.Sign(artifactKey, append([]byte(domain), cbor(manifest)...))
		cases = append(cases, documentCase{name, accepted, string(jsonBytes(map[string]any{"manifest": manifest, "signature": signature}))})
	}
	grant := func(m map[string]any) map[string]any { return m["capability_grants"].(map[string]any) }
	entries := func(m map[string]any) []any { return grant(m)["entries"].([]any) }
	http := func(m map[string]any) map[string]any { return entries(m)[0].(map[string]any) }
	storage := func(m map[string]any) map[string]any { return entries(m)[1].(map[string]any) }
	add("valid-both", true, func(map[string]any) {}, protocol.ArtifactDomainV3)
	add("empty-entries-deny", true, func(m map[string]any) { grant(m)["entries"] = []any{} }, protocol.ArtifactDomainV3)
	add("empty-permissions-deny", true, func(m map[string]any) { http(m)["permissions"] = []any{}; storage(m)["permissions"] = []any{} }, protocol.ArtifactDomainV3)
	add("empty-restrictions-deny", true, func(m map[string]any) {
		http(m)["origins"] = []any{}
		http(m)["methods"] = []any{}
		storage(m)["namespaces"] = []any{}
	}, protocol.ArtifactDomainV3)
	for index, item := range origins {
		add(fmt.Sprintf("origin-%02d", index), item.Accepted, func(m map[string]any) { http(m)["origins"] = []any{item.Value} }, protocol.ArtifactDomainV3)
	}
	for index, item := range namespaces {
		add(fmt.Sprintf("namespace-%02d", index), item.Accepted, func(m map[string]any) { storage(m)["namespaces"] = []any{item.Value} }, protocol.ArtifactDomainV3)
	}
	for _, field := range []string{"schema", "schema_sha256", "entries"} {
		add("missing-grants-"+field, false, func(m map[string]any) { delete(grant(m), field) }, protocol.ArtifactDomainV3)
	}
	for _, field := range []string{"capability_id", "schema_sha256", "permissions", "origins", "methods", "namespaces"} {
		add("missing-entry-"+field, false, func(m map[string]any) { delete(http(m), field) }, protocol.ArtifactDomainV3)
	}
	for _, field := range []string{"schema", "protocol", "scope", "limits", "capability_grants", "capability_hashes", "state_min", "asset_hashes"} {
		add("missing-manifest-"+field, false, func(m map[string]any) { delete(m, field) }, protocol.ArtifactDomainV3)
	}
	add("unknown-grants-field", false, func(m map[string]any) { grant(m)["extra"] = true }, protocol.ArtifactDomainV3)
	add("unknown-entry-field", false, func(m map[string]any) { http(m)["extra"] = true }, protocol.ArtifactDomainV3)
	add("schema-case-alias", false, func(m map[string]any) { m["SCHEMA"] = uint64(2) }, protocol.ArtifactDomainV3)
	add("entry-case-alias", false, func(m map[string]any) { http(m)["Permissions"] = []any{} }, protocol.ArtifactDomainV3)
	add("wrong-descriptor-hash", false, func(m map[string]any) { grant(m)["schema_sha256"] = protocol.Hash(nil) }, protocol.ArtifactDomainV3)
	add("wrong-descriptor-schema", false, func(m map[string]any) { grant(m)["schema"] = uint64(2) }, protocol.ArtifactDomainV3)
	add("wrong-entry-schema-hash", false, func(m map[string]any) { http(m)["schema_sha256"] = protocol.StorageGrantSHA256 }, protocol.ArtifactDomainV3)
	add("unbound-entry", false, func(m map[string]any) { delete(m["capability_hashes"].(map[string]any), protocol.HTTPGrantID) }, protocol.ArtifactDomainV3)
	add("unknown-capability", false, func(m map[string]any) { storage(m)["capability_id"] = "storage.unknown.v1" }, protocol.ArtifactDomainV3)
	add("reversed-entries", false, func(m map[string]any) { e := entries(m); e[0], e[1] = e[1], e[0] }, protocol.ArtifactDomainV3)
	add("duplicate-entries", false, func(m map[string]any) { e := entries(m); e[1] = e[0] }, protocol.ArtifactDomainV3)
	add("excess-entries", false, func(m map[string]any) { grant(m)["entries"] = append(entries(m), entries(m)[1]) }, protocol.ArtifactDomainV3)
	for _, field := range []string{"permissions", "origins", "methods"} {
		add("duplicate-"+field, false, func(m map[string]any) { v := http(m)[field].([]any)[0]; http(m)[field] = []any{v, v} }, protocol.ArtifactDomainV3)
	}
	add("duplicate-namespaces", false, func(m map[string]any) { storage(m)["namespaces"] = []any{"drafts", "drafts"} }, protocol.ArtifactDomainV3)
	add("reversed-origins", false, func(m map[string]any) { http(m)["origins"] = []any{"https://z.example", "https://a.example"} }, protocol.ArtifactDomainV3)
	add("reversed-methods", false, func(m map[string]any) { http(m)["methods"] = []any{"POST", "GET"} }, protocol.ArtifactDomainV3)
	add("reversed-namespaces", false, func(m map[string]any) { storage(m)["namespaces"] = []any{"drafts", "Drafts"} }, protocol.ArtifactDomainV3)
	add("wrong-array-type", false, func(m map[string]any) { http(m)["methods"] = "GET" }, protocol.ArtifactDomainV3)
	add("wrong-string-type", false, func(m map[string]any) { http(m)["methods"] = []any{uint64(1)} }, protocol.ArtifactDomainV3)
	add("wrong-permission", false, func(m map[string]any) { http(m)["permissions"] = []any{"storage.appPrivate"} }, protocol.ArtifactDomainV3)
	add("wrong-method", false, func(m map[string]any) { http(m)["methods"] = []any{"OPTIONS"} }, protocol.ArtifactDomainV3)
	add("HTTP-namespace", false, func(m map[string]any) { http(m)["namespaces"] = []any{"drafts"} }, protocol.ArtifactDomainV3)
	add("storage-origin", false, func(m map[string]any) { storage(m)["origins"] = []any{"https://example.com"} }, protocol.ArtifactDomainV3)
	add("storage-method", false, func(m map[string]any) { storage(m)["methods"] = []any{"GET"} }, protocol.ArtifactDomainV3)
	for _, count := range []int{32, 33} {
		add(fmt.Sprintf("origin-count-%d", count), count == 32, func(m map[string]any) {
			v := []any{}
			for i := 0; i < count; i++ {
				v = append(v, fmt.Sprintf("https://a%02d.example", i))
			}
			http(m)["origins"] = v
		}, protocol.ArtifactDomainV3)
	}
	for _, count := range []int{32, 33} {
		add(fmt.Sprintf("namespace-count-%d", count), count == 32, func(m map[string]any) {
			v := []any{}
			for i := 0; i < count; i++ {
				v = append(v, fmt.Sprintf("ns%02d", i))
			}
			storage(m)["namespaces"] = v
		}, protocol.ArtifactDomainV3)
	}
	add("all-known-methods", true, func(m map[string]any) { http(m)["methods"] = []any{"DELETE", "GET", "HEAD", "PATCH", "POST", "PUT"} }, protocol.ArtifactDomainV3)
	add("v1-signature-domain", false, func(map[string]any) {}, protocol.ArtifactDomain)
	add("assignment-signature-domain", false, func(map[string]any) {}, protocol.AssignmentDomainV3)
	// Duplicate key spellings must be rejected before any JSON-to-map conversion.
	duplicate := strings.Replace(cases[0].JSON, `"schema":3`, `"schema":3,"\u0073chema":3`, 1)
	cases = append(cases, documentCase{"escaped-duplicate-schema", false, duplicate})
	unknownEnvelope := strings.TrimSuffix(cases[0].JSON, "}") + `,"surprise":true}`
	cases = append(cases, documentCase{"unknown-envelope", false, unknownEnvelope})
	// Numeric byte arrays, ignored CR/LF and nonzero base64 pad bits can otherwise
	// decode to exactly the same signed bytes. V2 requires canonical base64 text.
	envelope := value([]byte(cases[0].JSON)).(map[string]any)
	signatureText := envelope["signature"].(string)
	signatureBytes, e := base64.StdEncoding.DecodeString(signatureText)
	must(e)
	byteArray := []uint64{}
	for _, item := range signatureBytes {
		byteArray = append(byteArray, uint64(item))
	}
	alphabet := "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
	noncanonical := []byte(signatureText)
	noncanonical[len(noncanonical)-3] = alphabet[strings.IndexByte(alphabet, noncanonical[len(noncanonical)-3])+1]
	for _, item := range []struct {
		name      string
		signature any
	}{
		{"signature-as-numeric-array", byteArray},
		{"signature-ignored-newline", signatureText[:16] + "\n" + signatureText[16:]},
		{"signature-nonzero-pad-bits", string(noncanonical)},
		{"signature-missing-padding", strings.TrimRight(signatureText, "=")},
		{"signature-short", base64.StdEncoding.EncodeToString(signatureBytes[:63])},
		{"signature-nonstring", uint64(1)},
	} {
		envelope["signature"] = item.signature
		cases = append(cases, documentCase{item.name, false, string(jsonBytes(envelope))})
	}
	add("v2-signature-domain", false, func(map[string]any) {}, protocol.ArtifactDomainV2)
	for _, field := range []string{"schema", "protocol", "guest_abi", "ui_schema"} {
		add("wrong-tuple-"+field, false, func(m map[string]any) { m[field] = uint64(99) }, protocol.ArtifactDomainV3)
	}
	for _, old := range []uint64{1, 2} {
		add(fmt.Sprintf("legacy-tuple-%d", old), false, func(m map[string]any) { m["schema"] = old; m["protocol"] = old; m["guest_abi"] = uint64(1) }, protocol.ArtifactDomainV3)
	}
	add("unknown-hash-only-capability", false, func(m map[string]any) {
		m["capability_hashes"].(map[string]any)["new.capability.v1"] = protocol.Hash(nil)
	}, protocol.ArtifactDomainV3)
	add("wrong-hash-only-capability", false, func(m map[string]any) {
		grant(m)["entries"] = []any{}
		m["capability_hashes"].(map[string]any)[protocol.HTTPGrantID] = protocol.Hash(nil)
	}, protocol.ArtifactDomainV3)
	for field, ceiling := range map[string]uint64{"memory_bytes": protocol.MaxV3MemoryBytes, "fuel": protocol.MaxV3Fuel, "startup_milliseconds": protocol.MaxV3StartupMilliseconds} {
		for _, n := range []uint64{0, 1, ceiling, ceiling + 1, ^uint64(0)} {
			add(fmt.Sprintf("limit-%s-%d", field, n), n > 0 && n <= ceiling, func(m map[string]any) { m["limits"].(map[string]any)[field] = n }, protocol.ArtifactDomainV3)
		}
	}
	for _, field := range []string{"scope", "limits", "capability_grants", "capability_hashes", "asset_hashes"} {
		body := value([]byte(cases[0].JSON)).(map[string]any)
		body["manifest"].(map[string]any)[field] = nil
		cases = append(cases, documentCase{"null-" + field, false, string(jsonBytes(body))})
	}
	for _, token := range []string{"3.0", "3e0", "-0", "03", "true", `"3"`, "18446744073709551616"} {
		cases = append(cases, documentCase{"schema-token-" + token, false, strings.Replace(cases[0].JSON, `"schema":3`, `"schema":`+token, 1)})
	}
	cases = append(cases, documentCase{"trailing-document", false, cases[0].JSON + "{}"})
	cases = append(cases, documentCase{"document-limit-plus-one", false, strings.Repeat(" ", protocol.MaxV3DocumentBytes+1-len(cases[0].JSON)) + cases[0].JSON})
	cases = append(cases, documentCase{"document-limit-exact", true, strings.Repeat(" ", protocol.MaxV3DocumentBytes-len(cases[0].JSON)) + cases[0].JSON})
	type assignmentCase struct {
		Name     string `json:"name"`
		Accepted bool   `json:"accepted"`
		JSON     string `json:"signed_assignment_json"`
	}
	assignmentCases := []assignmentCase{}
	addAssignment := func(name string, accepted bool, mutate func(map[string]any), domain string) {
		body := value(jsonBytes(a)).(map[string]any)
		mutate(body)
		signature := ed25519.Sign(assignmentKey, append([]byte(domain), cbor(body)...))
		assignmentCases = append(assignmentCases, assignmentCase{name, accepted, string(jsonBytes(map[string]any{"assignment": body, "signature": signature}))})
	}
	addAssignment("valid", true, func(map[string]any) {}, protocol.AssignmentDomainV3)
	for field := range value(jsonBytes(a)).(map[string]any) {
		addAssignment("missing-"+field, false, func(a map[string]any) { delete(a, field) }, protocol.AssignmentDomainV3)
	}
	for _, n := range []uint64{0, 6, 7, 8, ^uint64(0)} {
		addAssignment(fmt.Sprintf("sequence-%d", n), n > 6, func(a map[string]any) { a["sequence"] = n }, protocol.AssignmentDomainV3)
	}
	addAssignment("zero-rollout", false, func(a map[string]any) { a["rollout_basis_points"] = uint64(0) }, protocol.AssignmentDomainV3)
	addAssignment("rollout-over-limit", false, func(a map[string]any) { a["rollout_basis_points"] = uint64(10001) }, protocol.AssignmentDomainV3)
	for _, field := range []string{"channel", "release_id", "runtime", "artifact_sha256", "key_id", "cohort"} {
		addAssignment("wrong-"+field, false, func(a map[string]any) { a[field] = "wrong" }, protocol.AssignmentDomainV3)
	}
	addAssignment("wrong-scope", false, func(a map[string]any) { a["scope"].(map[string]any)["app"] = "other" }, protocol.AssignmentDomainV3)
	for _, schema := range []uint64{1, 2, 4} {
		addAssignment(fmt.Sprintf("wrong-schema-%d", schema), false, func(a map[string]any) { a["schema"] = schema }, protocol.AssignmentDomainV3)
	}
	addAssignment("unknown-field", false, func(a map[string]any) { a["extra"] = true }, protocol.AssignmentDomainV3)
	for _, domain := range []string{protocol.AssignmentDomain, protocol.AssignmentDomainV2, protocol.ArtifactDomainV3} {
		addAssignment("wrong-domain-"+strings.TrimSuffix(domain, "\x00"), false, func(map[string]any) {}, domain)
	}
	goodAssignment := assignmentCases[0].JSON
	assignmentCases = append(assignmentCases, assignmentCase{"escaped-duplicate-schema", false, strings.Replace(goodAssignment, `"schema":3`, `"schema":3,"\u0073chema":3`, 1)})
	assignmentCases = append(assignmentCases, assignmentCase{"document-limit-exact", true, strings.Repeat(" ", protocol.MaxV3DocumentBytes-len(goodAssignment)) + goodAssignment})
	assignmentCases = append(assignmentCases, assignmentCase{"document-limit-plus-one", false, strings.Repeat(" ", protocol.MaxV3DocumentBytes+1-len(goodAssignment)) + goodAssignment})
	sort.Slice(cases, func(i, j int) bool { return cases[i].Name < cases[j].Name })
	sort.Slice(assignmentCases, func(i, j int) bool { return assignmentCases[i].Name < assignmentCases[j].Name })
	corpus := map[string]any{"test_only": true, "description": "Original Go-generated signed hostile and valid v3 documents; representable values use exact unchanged CBOR. Never normalize grants or lexical input before verification.", "cases": cases, "assignment_cases": assignmentCases, "origin_cases": origins, "namespace_cases": namespaces}
	for _, relative := range []string{"services/protocol/testdata"} {
		directory := filepath.Join(*repository, relative)
		write(filepath.Join(directory, "signed-release-v3.json"), vector)
		write(filepath.Join(directory, "release-v3-cases.json"), corpus)
	}
	fmt.Printf("TEST ONLY v3 fixture %s; descriptor %s; signed cases %d\n", digest, protocol.GrantSchemaSHA256, len(cases))
}
func mustRead(path string) []byte { b, e := os.ReadFile(path); must(e); return b }
