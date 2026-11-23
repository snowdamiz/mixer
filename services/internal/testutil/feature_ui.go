package testutil

import (
	"bytes"
	"crypto/ed25519"
	"encoding/json"
	"strconv"
	"testing"

	"mixer/services/protocol"
)

const FeatureUINamespace = "drafts"

func FeatureUI(t testing.TB) (Fixture, protocol.FeatureUIEnrollment) {
	t.Helper()
	f := New(t).Protocol3()
	f.Host.UISchema = 3
	f.Host.CapabilityHashes = map[string]string{protocol.StorageGrantID: protocol.StorageGrantSHA256}
	d := protocol.Hash([]byte("test descriptor member"))
	ui := "2aa7ea5a007be20decffb7a35f450e89e7e77691bbaef4694c7f9456ba7787fc"
	grant := JSON(t, map[string]any{
		"capability_id": protocol.StorageGrantID, "schema_sha256": protocol.StorageGrantSHA256,
		"permissions": []string{"storage.appPrivate"}, "namespaces": []string{FeatureUINamespace},
		"origins": []string{}, "methods": []string{},
	})
	descriptor := JSON(t, map[string]any{
		"schema": 2,
		"application": map[string]any{
			"organization": f.Host.Scope.Organization, "project": f.Host.Scope.Project, "app": f.Host.Scope.App,
			"environment": f.Host.Scope.Environment, "bundle_id": "test.mixer.fieldlog",
		},
		"platform": map[string]any{
			"os": "ios", "architecture": "arm64", "environment": "simulator", "minimum_os": "26.0",
			"target": "arm64-apple-ios26.0-simulator",
		},
		"engine": map[string]any{
			"version": "test", "source_sha256": d, "artifact_sha256": d, "profile": "mixer-table-memory-v3",
			"guest_abi": 2, "ui_schema": 3, "ui_contract_sha256": ui,
			"capability_contract_sha256": "ca53c3c2ea1d8f08020468cc5d458d86542e0806d6494840557e591342f1154e",
		},
		"toolchain": map[string]any{
			"compiler_version": "test", "compiler_sha256": d, "sdk_version": "test",
			"sdk_sha256": d, "build_tools_sha256": d,
		},
		"dependencies": []map[string]any{
			{"id": "mixer.guest-ui-event-v3", "version": "3", "artifact_sha256": ui},
			{"id": "mixer.guest-ui-native-header-v3", "version": "3", "artifact_sha256": "875c5d4c81ed0e98fd334d198eae26e8287b6f1f47baa93b36a470380aa2d8d9"},
		},
		"capabilities": []map[string]any{{
			"id": protocol.StorageGrantID, "schema_sha256": protocol.StorageGrantSHA256,
			"native_sha256": d, "configuration_sha256": d, "grants_sha256": protocol.Hash(append(grant, '\n')),
		}},
		"build": map[string]any{
			"configuration": "debug", "settings_sha256": d, "generated_bridge_sha256": d, "link_inputs_sha256": d,
			"native_fallback_sha256": d, "permissions_sha256": d, "entitlements_sha256": d,
			"trust_roots_sha256": d, "resource_policy_sha256": d,
		},
		"execution": map[string]any{
			"startup_export": "mixer_guest_ui_start_v3", "startup_ms": f.Host.Limits.StartupMilliseconds,
			"max_payload_bytes": f.Host.MaxPayloadBytes, "memory_bytes": f.Host.Limits.MemoryBytes,
			"fuel": f.Host.Limits.Fuel, "operand_stack": 32, "call_depth": 8,
			"host_calls": 4, "state_schema": f.Host.StateVersion, "protocol": 3,
		},
		"capability_execution": map[string]any{
			"route":                "capability-guest-v1",
			"contract_sha256":      "898ea22b93a5b0dcd94c3b54f7cc97c41a259cd2285cbacd54bf0bd52ba48c97",
			"transport_sha256":     "052ebe9fbdc20a41307332086767e7903680bc83ba273c696edf9187be6b6439",
			"native_header_sha256": "9213c34ebf0f14d14f3319172e83647f704f3a02a60d413b4de990884357b4a6",
			"maximum_requests":     2, "reservation_bytes": 4096, "timeout_milliseconds": 100,
			"turn_milliseconds": 4, "bridge_policy_sha256": d,
		},
	})
	pin := RebindFeatureUIRoots(t, protocol.FeatureUIEnrollment{
		Scope: f.Host.Scope, DescriptorJSON: descriptor,
		StoragePolicy: protocol.ReadOnlyStorage{Namespace: FeatureUINamespace, Operations: []string{"get"}},
	}, f.Roots)
	f.Host.Runtime = pin.Fingerprint
	return f, pin
}

func RebindFeatureUIRoots(t testing.TB, pin protocol.FeatureUIEnrollment, roots []protocol.Root) protocol.FeatureUIEnrollment {
	t.Helper()
	pin.TrustRootsJSON = JSON(t, roots)
	decoder := json.NewDecoder(bytes.NewReader(pin.DescriptorJSON))
	decoder.UseNumber()
	var descriptor map[string]any
	if err := decoder.Decode(&descriptor); err != nil {
		t.Fatal(err)
	}
	build, ok := descriptor["build"].(map[string]any)
	if !ok {
		t.Fatal("descriptor has no build object")
	}
	build["trust_roots_sha256"] = protocol.Hash(pin.TrustRootsJSON)
	pin.DescriptorJSON = JSON(t, descriptor)
	canonical, err := protocol.CanonicalCBOR(descriptorCBORValues(t, descriptor))
	if err != nil {
		t.Fatal(err)
	}
	pin.Fingerprint = protocol.Hash(append([]byte("mixer.runtime.identity.v2\x00"), canonical...))
	return pin
}

func descriptorCBORValues(t testing.TB, value any) any {
	t.Helper()
	switch v := value.(type) {
	case map[string]any:
		for key, child := range v {
			v[key] = descriptorCBORValues(t, child)
		}
	case []any:
		for i, child := range v {
			v[i] = descriptorCBORValues(t, child)
		}
	case json.Number:
		n, err := strconv.ParseUint(string(v), 10, 64)
		if err != nil {
			t.Fatal(err)
		}
		return n
	}
	return value
}

func JSON(t testing.TB, value any) []byte {
	t.Helper()
	b, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	return b
}

func (f Fixture) FeatureUIManifest(t testing.TB, payload []byte, id string) protocol.SignedManifestV3 {
	t.Helper()
	m := f.manifestV3(payload, id)
	m.UISchema = 3
	m.CapabilityGrants.Entries = m.CapabilityGrants.Entries[1:]
	m.CapabilityGrants.Entries[0].Namespaces = []string{FeatureUINamespace}
	return SignFeatureUIManifest(t, m, f.ArtifactKey)
}

// SignFeatureUIManifest uses the v3 wire domain for test fixtures, including
// correctly signed negative cases. The default v3 signer admits only UI1.
func SignFeatureUIManifest(t testing.TB, m protocol.ManifestV3, key ed25519.PrivateKey) protocol.SignedManifestV3 {
	t.Helper()
	wire, err := protocol.CanonicalCBOR(m)
	if err != nil {
		t.Fatal(err)
	}
	return protocol.SignedManifestV3{
		Manifest: m, Signature: ed25519.Sign(key, append([]byte(protocol.ArtifactDomainV3), wire...)),
	}
}
