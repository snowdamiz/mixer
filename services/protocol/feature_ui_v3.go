package protocol

import (
	"encoding/json"
	"fmt"
	"slices"
	"strconv"
	"strings"
)

const featureUIContract = "2aa7ea5a007be20decffb7a35f450e89e7e77691bbaef4694c7f9456ba7787fc"
const featureUIHeader = "875c5d4c81ed0e98fd334d198eae26e8287b6f1f47baa93b36a470380aa2d8d9"
const featureUIDescriptorLimit = 131072

// FeatureUIEnrollment supplies the installed identity pinned by the operator.
type FeatureUIEnrollment struct {
	Scope          Scope           `json:"scope"`
	Fingerprint    string          `json:"fingerprint"`
	DescriptorJSON []byte          `json:"descriptor_json"`
	TrustRootsJSON []byte          `json:"trust_roots_json"`
	StoragePolicy  ReadOnlyStorage `json:"storage_policy"`
}

// ReadOnlyStorage binds the namespace to the descriptor's grant digest and
// requires the operator to declare get-only access. The installed Swift
// adapter enforces the actual operations and readable keys.
type ReadOnlyStorage struct {
	Namespace  string   `json:"namespace"`
	Operations []string `json:"operations"`
}

// FeatureUIV3 owns the scoped origin verifier for one authenticated runtime.
type FeatureUIV3 struct {
	host      Host
	roots     []Root
	namespace string
}

func NewFeatureUIV3(pin FeatureUIEnrollment) (*FeatureUIV3, error) {
	if len(pin.DescriptorJSON) > featureUIDescriptorLimit || len(pin.TrustRootsJSON) > MaxV3DocumentBytes {
		return nil, fmt.Errorf("feature UI enrollment documents exceed bounds")
	}
	var d featureUIDescriptor
	if err := decodeJSON(pin.DescriptorJSON, &d, true); err != nil {
		return nil, fmt.Errorf("feature UI descriptor: %w", err)
	}
	canonical, err := CanonicalCBOR(d)
	if err != nil || len(canonical) > featureUIDescriptorLimit ||
		Hash(append([]byte("mixer.runtime.identity.v2\x00"), canonical...)) != pin.Fingerprint {
		return nil, fmt.Errorf("feature UI runtime fingerprint mismatch")
	}
	host, err := d.host(pin.Fingerprint)
	if err != nil {
		return nil, err
	}
	if host.Scope != pin.Scope {
		return nil, fmt.Errorf("feature UI descriptor scope mismatch")
	}
	if Hash(pin.TrustRootsJSON) != d.Build.TrustRoots {
		return nil, fmt.Errorf("feature UI trust roots digest mismatch")
	}
	var roots []Root
	if err := DecodeJSON(pin.TrustRootsJSON, &roots); err != nil {
		return nil, fmt.Errorf("feature UI trust roots: %w", err)
	}
	if err := validateRootsV3(roots); err != nil {
		return nil, err
	}
	for _, root := range roots {
		if root.Scope != pin.Scope {
			return nil, fmt.Errorf("feature UI root scope mismatch")
		}
	}
	storage := pin.StoragePolicy
	if !validNamespace(storage.Namespace) || !slices.Equal(storage.Operations, []string{"get"}) {
		return nil, fmt.Errorf("feature UI storage requires a valid namespace and operations [get]")
	}
	// Swift hashes the lexicographically sorted grant JSON followed by LF.
	grantBytes, err := json.Marshal(map[string]any{
		"capability_id": StorageGrantID, "schema_sha256": StorageGrantSHA256,
		"permissions": []string{"storage.appPrivate"}, "namespaces": []string{storage.Namespace},
		"origins": []string{}, "methods": []string{},
	})
	if err != nil || Hash(append(grantBytes, '\n')) != d.Capabilities[0].Grants {
		return nil, fmt.Errorf("feature UI storage grant digest mismatch")
	}
	return &FeatureUIV3{host: host, roots: roots, namespace: storage.Namespace}, nil
}

func (p *FeatureUIV3) Scope() Scope    { return p.host.Scope }
func (p *FeatureUIV3) Runtime() string { return p.host.Runtime }

// ValidateFeatureUIV3Record checks persistent wire structure. Serving or
// admitting the record requires a FeatureUIV3 verifier from startup.
func ValidateFeatureUIV3Record(m ManifestV3) error {
	if err := m.validateForUI(3); err != nil {
		return err
	}
	entries := m.CapabilityGrants.Entries
	if len(m.CapabilityHashes) != 1 || len(entries) != 1 || entries[0].CapabilityID != StorageGrantID ||
		!slices.Equal(entries[0].Permissions, []string{"storage.appPrivate"}) || len(entries[0].Namespaces) != 1 {
		return fmt.Errorf("feature UI requires one exact private-storage namespace grant")
	}
	return nil
}

func (p *FeatureUIV3) compatible(m ManifestV3) error {
	if err := ValidateFeatureUIV3Record(m); err != nil {
		return err
	}
	if m.CapabilityGrants.Entries[0].Namespaces[0] != p.namespace {
		return fmt.Errorf("feature UI storage namespace differs from enrollment")
	}
	return compatibleV3Fields(m, p.host)
}

func (p *FeatureUIV3) VerifyManifest(s SignedManifestV3, payload []byte, now uint64) error {
	if err := verifyManifestHeaderV3(s, p.roots, now, p.compatible); err != nil {
		return err
	}
	return verifyPayloadV3(s.Manifest, payload)
}

func (p *FeatureUIV3) VerifyAssignment(s SignedAssignmentV3, m SignedManifestV3, channel string, last, now uint64) error {
	if err := verifyManifestHeaderV3(m, p.roots, now, p.compatible); err != nil {
		return err
	}
	return p.verifyAssignment(s, m.Manifest, channel, last, now)
}

// VerifyHalt allows a current assignment signer to remove eligibility even
// after an enrolled artifact's signature has expired.
func (p *FeatureUIV3) VerifyHalt(s SignedAssignmentV3, m ManifestV3, channel string, last, now uint64) error {
	if err := p.compatible(m); err != nil {
		return err
	}
	return p.verifyAssignment(s, m, channel, last, now)
}

func (p *FeatureUIV3) verifyAssignment(s SignedAssignmentV3, m ManifestV3, channel string, last, now uint64) error {
	if err := s.Assignment.Validate(); err != nil {
		return err
	}
	return verifyAssignmentBindingV3(s, m, p.roots, channel, last, now)
}

type featureUIDescriptor struct {
	Schema      uint64 `json:"schema"`
	Application struct {
		Organization string `json:"organization"`
		Project      string `json:"project"`
		App          string `json:"app"`
		Environment  string `json:"environment"`
		BundleID     string `json:"bundle_id"`
	} `json:"application"`
	Platform struct {
		OS           string `json:"os"`
		Architecture string `json:"architecture"`
		Environment  string `json:"environment"`
		MinimumOS    string `json:"minimum_os"`
		Target       string `json:"target"`
	} `json:"platform"`
	Engine struct {
		Version            string `json:"version"`
		Source             string `json:"source_sha256"`
		Artifact           string `json:"artifact_sha256"`
		Profile            string `json:"profile"`
		GuestABI           uint64 `json:"guest_abi"`
		UISchema           uint64 `json:"ui_schema"`
		UIContract         string `json:"ui_contract_sha256"`
		CapabilityContract string `json:"capability_contract_sha256"`
	} `json:"engine"`
	Toolchain struct {
		CompilerVersion string `json:"compiler_version"`
		Compiler        string `json:"compiler_sha256"`
		SDKVersion      string `json:"sdk_version"`
		SDK             string `json:"sdk_sha256"`
		BuildTools      string `json:"build_tools_sha256"`
	} `json:"toolchain"`
	Dependencies []struct {
		ID       string `json:"id"`
		Version  string `json:"version"`
		Artifact string `json:"artifact_sha256"`
	} `json:"dependencies"`
	Capabilities []struct {
		ID            string `json:"id"`
		Schema        string `json:"schema_sha256"`
		Native        string `json:"native_sha256"`
		Configuration string `json:"configuration_sha256"`
		Grants        string `json:"grants_sha256"`
	} `json:"capabilities"`
	Build struct {
		Configuration   string `json:"configuration"`
		Settings        string `json:"settings_sha256"`
		GeneratedBridge string `json:"generated_bridge_sha256"`
		LinkInputs      string `json:"link_inputs_sha256"`
		NativeFallback  string `json:"native_fallback_sha256"`
		Permissions     string `json:"permissions_sha256"`
		Entitlements    string `json:"entitlements_sha256"`
		TrustRoots      string `json:"trust_roots_sha256"`
		ResourcePolicy  string `json:"resource_policy_sha256"`
	} `json:"build"`
	Execution struct {
		StartupExport   string `json:"startup_export"`
		StartupMS       uint64 `json:"startup_ms"`
		MaxPayloadBytes uint64 `json:"max_payload_bytes"`
		MemoryBytes     uint64 `json:"memory_bytes"`
		Fuel            uint64 `json:"fuel"`
		OperandStack    uint64 `json:"operand_stack"`
		CallDepth       uint64 `json:"call_depth"`
		HostCalls       uint64 `json:"host_calls"`
		StateSchema     uint64 `json:"state_schema"`
		Protocol        uint64 `json:"protocol"`
	} `json:"execution"`
	CapabilityExecution struct {
		Route            string `json:"route"`
		Contract         string `json:"contract_sha256"`
		Transport        string `json:"transport_sha256"`
		NativeHeader     string `json:"native_header_sha256"`
		MaximumRequests  uint64 `json:"maximum_requests"`
		ReservationBytes uint64 `json:"reservation_bytes"`
		TimeoutMS        uint64 `json:"timeout_milliseconds"`
		TurnMS           uint64 `json:"turn_milliseconds"`
		BridgePolicy     string `json:"bridge_policy_sha256"`
	} `json:"capability_execution"`
}

func (d featureUIDescriptor) host(fingerprint string) (Host, error) {
	a, p, e, x, c := d.Application, d.Platform, d.Engine, d.Execution, d.CapabilityExecution
	if d.Schema != 2 || !ValidID(a.BundleID) || !d.validPlatform() ||
		e.Profile != "mixer-table-memory-v3" || e.UIContract != featureUIContract ||
		e.CapabilityContract != "ca53c3c2ea1d8f08020468cc5d458d86542e0806d6494840557e591342f1154e" ||
		x.StartupExport != "mixer_guest_ui_start_v3" || x.OperandStack == 0 || x.OperandStack > 4096 ||
		x.CallDepth == 0 || x.CallDepth > 64 || x.HostCalls > 1024 ||
		c.Route != "capability-guest-v1" ||
		c.Contract != "898ea22b93a5b0dcd94c3b54f7cc97c41a259cd2285cbacd54bf0bd52ba48c97" ||
		c.Transport != "052ebe9fbdc20a41307332086767e7903680bc83ba273c696edf9187be6b6439" ||
		c.NativeHeader != "9213c34ebf0f14d14f3319172e83647f704f3a02a60d413b4de990884357b4a6" ||
		c.MaximumRequests == 0 || c.MaximumRequests > 8 || c.ReservationBytes == 0 || c.ReservationBytes > 8388608 ||
		c.TimeoutMS == 0 || c.TimeoutMS > 30000 || c.TurnMS == 0 || c.TurnMS > 50 ||
		(d.Build.Configuration != "debug" && d.Build.Configuration != "release") {
		return Host{}, fmt.Errorf("invalid feature UI installed descriptor contract")
	}
	if len(d.Capabilities) != 1 || d.Capabilities[0].ID != StorageGrantID || d.Capabilities[0].Schema != StorageGrantSHA256 {
		return Host{}, fmt.Errorf("feature UI descriptor requires only private storage")
	}
	want := map[string]string{"mixer.guest-ui-event-v3": featureUIContract, "mixer.guest-ui-native-header-v3": featureUIHeader}
	if len(d.Dependencies) > 128 {
		return Host{}, fmt.Errorf("feature UI descriptor has too many dependencies")
	}
	previous := ""
	for _, dep := range d.Dependencies {
		if !ValidID(dep.ID) || dep.ID <= previous || dep.ID == "mixer.fieldlog-compact-editor-v1" ||
			!identityLabel(dep.Version) || !ValidDigest(dep.Artifact) {
			return Host{}, fmt.Errorf("invalid feature UI descriptor dependency")
		}
		previous = dep.ID
		if digest, ok := want[dep.ID]; ok {
			if dep.Version != "3" || dep.Artifact != digest {
				return Host{}, fmt.Errorf("feature UI descriptor dependency mismatch")
			}
			delete(want, dep.ID)
		}
	}
	if len(want) != 0 {
		return Host{}, fmt.Errorf("missing feature UI descriptor dependency")
	}
	for _, label := range []string{e.Version, d.Toolchain.CompilerVersion, d.Toolchain.SDKVersion} {
		if !identityLabel(label) {
			return Host{}, fmt.Errorf("invalid feature UI descriptor label")
		}
	}
	b, t, storage := d.Build, d.Toolchain, d.Capabilities[0]
	for _, digest := range []string{e.Source, e.Artifact, t.Compiler, t.SDK, t.BuildTools, b.Settings,
		b.GeneratedBridge, b.LinkInputs, b.NativeFallback, b.Permissions, b.Entitlements, b.TrustRoots, b.ResourcePolicy,
		c.BridgePolicy, storage.Native, storage.Configuration, storage.Grants} {
		if !ValidDigest(digest) {
			return Host{}, fmt.Errorf("invalid feature UI descriptor digest")
		}
	}
	h := Host{
		Scope:   Scope{Organization: a.Organization, Project: a.Project, App: a.App, Environment: a.Environment, Platform: p.OS},
		Runtime: fingerprint, Protocol: x.Protocol, GuestABI: e.GuestABI, UISchema: e.UISchema,
		CapabilityHashes: map[string]string{StorageGrantID: StorageGrantSHA256},
		StateVersion:     x.StateSchema, MaxPayloadBytes: x.MaxPayloadBytes,
		Limits: Limits{MemoryBytes: x.MemoryBytes, Fuel: x.Fuel, StartupMilliseconds: x.StartupMS},
	}
	return h, validateHostV3ForUI(h, 3)
}

func identityLabel(s string) bool {
	if s == "" || len(s) > 256 || strings.TrimSpace(s) != s {
		return false
	}
	for _, b := range []byte(s) {
		if b < 32 || b > 126 {
			return false
		}
	}
	return true
}

func (d featureUIDescriptor) validPlatform() bool {
	p := d.Platform
	if (p.Architecture != "arm64" && p.Architecture != "x86_64") ||
		(p.Environment != "device" && p.Environment != "simulator") {
		return false
	}
	parse := func(s string) (uint64, bool) {
		n, err := strconv.ParseUint(s, 10, 16)
		return n, err == nil && strconv.FormatUint(n, 10) == s
	}
	switch p.OS {
	case "android":
		api, ok := parse(p.MinimumOS)
		arch := p.Architecture
		if arch == "arm64" {
			arch = "aarch64"
		}
		return ok && api >= 28 && p.Target == arch+"-unknown-linux-android"+p.MinimumOS
	case "ios":
		parts := strings.Split(p.MinimumOS, ".")
		if len(parts) < 2 || len(parts) > 3 {
			return false
		}
		for i, part := range parts {
			n, ok := parse(part)
			if !ok || (i == 0 && n < 17) {
				return false
			}
		}
		target := p.Architecture + "-apple-ios" + p.MinimumOS
		if p.Environment == "simulator" {
			target += "-simulator"
		} else if p.Architecture != "arm64" {
			return false
		}
		return p.Target == target
	default:
		return false
	}
}
