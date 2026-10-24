package protocol_test

import (
	"bytes"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"reflect"
	"testing"

	"mixer/services/protocol"
)

type legacyWireDocument struct {
	Name     string `json:"name"`
	Kind     string `json:"kind"`
	Accepted bool   `json:"accepted"`
	JSON     string `json:"json"`
}
type legacyWireCorpus struct {
	TestOnly         bool                      `json:"test_only"`
	Description      string                    `json:"description"`
	Host             protocol.Host             `json:"host"`
	Roots            []protocol.Root           `json:"roots"`
	Payload          []byte                    `json:"payload"`
	SignedManifest   protocol.SignedManifest   `json:"signed_manifest"`
	SignedAssignment protocol.SignedAssignment `json:"signed_assignment"`
	Now              uint64                    `json:"verification_time_unix"`
	Installation     string                    `json:"installation"`
	Last             uint64                    `json:"last_sequence"`
	ArtifactSHA256   string                    `json:"artifact_sha256"`
	ManifestCBOR     string                    `json:"manifest_cbor_hex"`
	AssignmentCBOR   string                    `json:"assignment_cbor_hex"`
	Documents        []legacyWireDocument      `json:"documents"`
}

func loadLegacyWire(t testing.TB) legacyWireCorpus {
	t.Helper()
	b, e := os.ReadFile("testdata/legacy-v1-wire-cases.json")
	if e != nil {
		t.Fatal(e)
	}
	var corpus legacyWireCorpus
	if e = protocol.DecodeJSON(b, &corpus); e != nil {
		t.Fatal(e)
	}
	if !corpus.TestOnly || len(corpus.Documents) != 271 {
		t.Fatal("missing original shared wire cases")
	}
	return corpus
}
func legacyWireCheck(v legacyWireCorpus, doc legacyWireDocument, decode func([]byte, any) error) error {
	switch doc.Kind {
	case "manifest":
		var signed protocol.SignedManifest
		if e := decode([]byte(doc.JSON), &signed); e != nil {
			return e
		}
		return protocol.VerifyManifest(signed, v.Payload, v.Roots, v.Host, v.Now)
	case "assignment":
		var signed protocol.SignedAssignment
		if e := decode([]byte(doc.JSON), &signed); e != nil {
			return e
		}
		return protocol.VerifyAssignment(signed, v.SignedManifest.Manifest, v.Roots, v.Host, "beta", v.Installation, v.Last, v.Now)
	case "host":
		var host protocol.Host
		if e := decode([]byte(doc.JSON), &host); e != nil {
			return e
		}
		return protocol.VerifyManifest(v.SignedManifest, v.Payload, v.Roots, host, v.Now)
	case "root":
		var root protocol.Root
		if e := decode([]byte(doc.JSON), &root); e != nil {
			return e
		}
		return protocol.VerifyManifest(v.SignedManifest, v.Payload, []protocol.Root{root, v.Roots[1]}, v.Host, v.Now)
	default:
		return fmt.Errorf("unknown wire case kind")
	}
}
func TestLegacyV1WireCorpusMatchesCanonicalContract(t *testing.T) {
	v := loadLegacyWire(t)
	for _, decoder := range []struct {
		name   string
		decode func([]byte, any) error
	}{{"DecodeJSON", protocol.DecodeJSON}, {"direct-Unmarshal", json.Unmarshal}} {
		t.Run(decoder.name, func(t *testing.T) {
			for _, doc := range v.Documents {
				t.Run(doc.Name, func(t *testing.T) {
					e := legacyWireCheck(v, doc, decoder.decode)
					if (e == nil) != doc.Accepted {
						t.Fatalf("accepted=%v expected=%v: %v", e == nil, doc.Accepted, e)
					}
				})
			}
		})
	}
	for _, pair := range []struct {
		value any
		hex   string
	}{{v.SignedManifest.Manifest, v.ManifestCBOR}, {v.SignedAssignment.Assignment, v.AssignmentCBOR}} {
		b, e := protocol.CanonicalCBOR(pair.value)
		if e != nil || hex.EncodeToString(b) != pair.hex {
			t.Fatal("canonical wire fixture changed", e)
		}
	}
	digest, e := protocol.ManifestDigest(v.SignedManifest.Manifest)
	if e != nil || digest != v.ArtifactSHA256 {
		t.Fatal("artifact identity changed", e)
	}
}

func TestGenericJSONShapePreservesDynamicKeysArraysRawValuesAndDefaults(t *testing.T) {
	type defaults struct {
		Name      string `json:"name,omitempty"`
		Defaulted uint64 `json:"defaulted,omitempty"`
	}
	config := defaults{Name: "existing-default", Defaulted: 17}
	if e := protocol.DecodeJSON([]byte(`{}`), &config); e != nil || config.Name != "existing-default" || config.Defaulted != 17 {
		t.Fatal("generic config defaults changed", e)
	}
	if e := protocol.DecodeJSON([]byte(`{"NAME":"alias"}`), &config); e == nil {
		t.Fatal("alternate fixed model name accepted")
	}
	type dynamic struct {
		Values []map[string]uint64          `json:"values"`
		Raw    json.RawMessage              `json:"raw"`
		Pairs  map[string]map[string]string `json:"pairs"`
	}
	var value dynamic
	raw := []byte(`{"values":[{"SCHEMA":1,"Schema":2,"schema":3},{"schema":4}],"raw":{"scope":{"SCHEMA":9,"schema":10}},"pairs":{"scope":{"Fuel":"upper","fuel":"lower"}}}`)
	if e := protocol.DecodeJSON(raw, &value); e != nil {
		t.Fatal("dynamic map incorrectly treated as fixed fields", e)
	}
	if value.Values[0]["SCHEMA"] != 1 || value.Values[0]["Schema"] != 2 || value.Values[0]["schema"] != 3 || value.Values[1]["schema"] != 4 || value.Pairs["scope"]["Fuel"] != "upper" {
		t.Fatal("dynamic keys/array order changed")
	}
	var rawValue map[string]any
	if e := json.Unmarshal(value.Raw, &rawValue); e != nil || rawValue["scope"] == nil {
		t.Fatal("RawMessage lost dynamic shape", e)
	}
	type outer struct {
		Payload struct {
			Sequence uint64 `json:"sequence"`
		} `json:"payload"`
	}
	var out outer
	var throughInterface any = &out
	if e := protocol.DecodeJSON([]byte(`{"Payload":{"sequence":1}}`), &throughInterface); e == nil {
		t.Fatal("interface-held concrete model bypassed exact field matching")
	}
	var maps map[string]map[string]uint64
	if e := protocol.DecodeJSON([]byte(`{"schema":{"SCHEMA":1,"schema":2},"SCHEMA":{"schema":3}}`), &maps); e != nil || maps["schema"]["SCHEMA"] != 1 || maps["SCHEMA"]["schema"] != 3 {
		t.Fatal("dynamic dictionary aliases collapsed", e)
	}
}

func TestClosedProtocolReusedReceiversReplaceMapsAndPreserveFailures(t *testing.T) {
	v := loadLegacyWire(t)
	v2 := loadV2(t)
	// Structural decode is not signature/profile authorization. Prepopulate stale
	// asset maps explicitly to prove an incoming empty object replaces them.
	old := v.SignedManifest.Manifest
	old.CapabilityHashes = map[string]string{"stale": protocol.Hash(nil)}
	old.AssetHashes = map[string]string{"stale": protocol.Hash(nil)}
	incoming := v.SignedManifest.Manifest
	incoming.CapabilityHashes = map[string]string{}
	incoming.AssetHashes = map[string]string{}
	if e := json.Unmarshal(encodedV2(t, incoming), &old); e != nil || len(old.CapabilityHashes) != 0 || len(old.AssetHashes) != 0 {
		t.Fatal("v1 maps merged prior receiver contents", e)
	}
	old2 := v2.SignedManifest.Manifest
	old2.CapabilityHashes = map[string]string{"stale": protocol.Hash(nil)}
	old2.AssetHashes = map[string]string{"stale": protocol.Hash(nil)}
	incoming2 := v2.SignedManifest.Manifest
	incoming2.CapabilityHashes = map[string]string{}
	incoming2.AssetHashes = map[string]string{}
	incoming2.CapabilityGrants.Entries = []protocol.CapabilityGrant{}
	if e := json.Unmarshal(encodedV2(t, incoming2), &old2); e != nil || len(old2.CapabilityHashes) != 0 || len(old2.AssetHashes) != 0 || len(old2.CapabilityGrants.Entries) != 0 {
		t.Fatal("v2 maps/grants merged prior receiver contents", e)
	}
	for _, initial := range []any{v.SignedManifest.Manifest, v.SignedAssignment.Assignment, v.Host, v.Roots[0], v.Host.Scope, v.Host.Limits, v.SignedManifest, v.SignedAssignment,
		v2.SignedManifest.Manifest, v2.SignedAssignment.Assignment, v2.SignedManifest, v2.SignedAssignment, v2.SignedManifest.Manifest.CapabilityGrants, v2.SignedManifest.Manifest.CapabilityGrants.Entries[0]} {
		typeOf := reflect.TypeOf(initial)
		t.Run(typeOf.Name(), func(t *testing.T) {
			receiver := reflect.New(typeOf)
			receiver.Elem().Set(reflect.ValueOf(initial))
			before := encodedV2(t, receiver.Interface())
			var fields map[string]json.RawMessage
			if e := json.Unmarshal(before, &fields); e != nil {
				t.Fatal(e)
			}
			// Keep all keys present and include a valid changed sibling. The bad
			// primitive reaches typed decoding, which would otherwise partly update
			// reused values even while returning an error.
			set := func(key string, value any) { fields[key] = encodedV2(t, value) }
			badManifest := func(raw json.RawMessage) json.RawMessage {
				var nested map[string]json.RawMessage
				if e := json.Unmarshal(raw, &nested); e != nil {
					t.Fatal(e)
				}
				nested["release_id"] = encodedV2(t, "changed-before-error")
				var limits map[string]json.RawMessage
				if e := json.Unmarshal(nested["limits"], &limits); e != nil {
					t.Fatal(e)
				}
				limits["fuel"] = encodedV2(t, "wrong-uint")
				nested["limits"] = encodedV2(t, limits)
				return encodedV2(t, nested)
			}
			switch typeOf.Name() {
			case "Manifest", "ManifestV2":
				fieldsRaw := badManifest(before)
				if e := json.Unmarshal(fieldsRaw, &fields); e != nil {
					t.Fatal(e)
				}
			case "Assignment", "AssignmentV2":
				set("release_id", "changed-before-error")
				set("sequence", "wrong-uint")
			case "Host":
				set("runtime", protocol.Hash([]byte("changed")))
				set("state_version", "wrong-uint")
			case "Root":
				set("key_id", "changed-before-error")
				set("not_before_unix", "wrong-uint")
			case "Scope":
				set("app", "changed-before-error")
				set("platform", map[string]string{"wrong": "type"})
			case "Limits":
				set("memory_bytes", uint64(1))
				set("fuel", "wrong-uint")
			case "SignedManifest", "SignedManifestV2":
				fields["manifest"] = badManifest(fields["manifest"])
				set("signature", make([]byte, 64))
			case "SignedAssignment", "SignedAssignmentV2":
				var nested map[string]json.RawMessage
				if e := json.Unmarshal(fields["assignment"], &nested); e != nil {
					t.Fatal(e)
				}
				nested["sequence"] = encodedV2(t, "wrong-uint")
				fields["assignment"] = encodedV2(t, nested)
				set("signature", make([]byte, 64))
			case "CapabilityGrants":
				set("entries", []any{})
				set("schema_sha256", "changed-before-error")
				set("schema", "wrong-uint")
			case "CapabilityGrant":
				set("capability_id", "changed-before-error")
				set("methods", "wrong-array")
			default:
				t.Fatal("missing receiver regression case")
			}
			if e := json.Unmarshal(encodedV2(t, fields), receiver.Interface()); e == nil {
				t.Fatal("expected typed model decode failure")
			}
			if !bytes.Equal(before, encodedV2(t, receiver.Interface())) {
				t.Fatal("failed model decode mutated receiver")
			}
		})
	}
	// Signed envelope replacement must also clear nested state atomically.
	signed := v.SignedManifest
	signed.Manifest.CapabilityHashes = map[string]string{"stale": protocol.Hash(nil)}
	if e := json.Unmarshal(encodedV2(t, v.SignedManifest), &signed); e != nil || !reflect.DeepEqual(signed, v.SignedManifest) {
		t.Fatal("nested v1 manifest merged", e)
	}
	signed2 := v2.SignedManifest
	signed2.Manifest.CapabilityHashes = map[string]string{"stale": protocol.Hash(nil)}
	if e := json.Unmarshal(encodedV2(t, v2.SignedManifest), &signed2); e != nil || !reflect.DeepEqual(signed2, v2.SignedManifest) {
		t.Fatal("nested v2 manifest merged", e)
	}
}

func TestSignedProtocolDocumentBoundsIncludeOuterWhitespace(t *testing.T) {
	v := loadLegacyWire(t)
	raw := encodedV2(t, v.SignedManifest)
	for _, extra := range []int{0, 1} {
		data := append(bytes.Clone(raw), bytes.Repeat([]byte(" "), 1_048_576-len(raw)+extra)...)
		var output protocol.SignedManifest
		e := protocol.DecodeJSON(data, &output)
		if (e == nil) != (extra == 0) {
			t.Fatalf("v1 boundary %d: %v", extra, e)
		}
	}
	v2 := loadV2(t)
	raw = encodedV2(t, v2.SignedManifest)
	for _, extra := range []int{0, 1} {
		data := append(bytes.Clone(raw), bytes.Repeat([]byte(" "), protocol.MaxV2DocumentBytes-len(raw)+extra)...)
		var output protocol.SignedManifestV2
		e := protocol.DecodeJSON(data, &output)
		if (e == nil) != (extra == 0) {
			t.Fatalf("v2 boundary %d: %v", extra, e)
		}
	}
}

func FuzzLegacySignedWireNeverPanics(f *testing.F) {
	v := loadLegacyWire(f)
	f.Add(encodedV2(f, v.SignedManifest))
	f.Add([]byte(`{"manifest":{"SCHEMA":1},"signature":[]}`))
	f.Add([]byte(`{"manifest":{},"signature":""}`))
	f.Fuzz(func(t *testing.T, data []byte) {
		if len(data) > 65536 {
			return
		}
		var signed protocol.SignedManifest
		if protocol.DecodeJSON(data, &signed) == nil {
			_ = protocol.VerifyManifest(signed, v.Payload, v.Roots, v.Host, v.Now)
		}
	})
}
