package protocol

import (
	"crypto/ed25519"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
)

const ArtifactDomainV2 = "mixer.artifact.v2\x00"
const AssignmentDomainV2 = "mixer.assignment.v2\x00"
const GrantSchemaSHA256 = "b394ffd165ef28977de9743b1c1a98c419504787f2912e30d419cfb1582e15e1"
const HTTPGrantID = "network.http.v1"
const HTTPGrantSHA256 = "fa1549c0a1e2e6b3bf4a83af1a6d37730bbefc8cddc3ffbe3c807d5e7af503f3"
const StorageGrantID = "storage.keyValue.v1"
const StorageGrantSHA256 = "4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd"
const MaxV2DocumentBytes = 65536

// These are signed protocol values, not independent execution authority. A
// native host must verify the payload/signatures and intersect these grants with
// its installed policy. Schema hashes alone grant no permission.
type CapabilityGrant struct {
	CapabilityID string   `json:"capability_id"`
	SchemaSHA256 string   `json:"schema_sha256"`
	Permissions  []string `json:"permissions"`
	Origins      []string `json:"origins"`
	Methods      []string `json:"methods"`
	Namespaces   []string `json:"namespaces"`
}

type CapabilityGrants struct {
	Schema       uint64            `json:"schema"`
	SchemaSHA256 string            `json:"schema_sha256"`
	Entries      []CapabilityGrant `json:"entries"`
}

// ManifestV2 is separate from Manifest so v1's exact fields and canonical bytes
// cannot accidentally acquire an optional or unsigned grants sidecar.
type ManifestV2 struct {
	Schema           uint64            `json:"schema"`
	Scope            Scope             `json:"scope"`
	ReleaseID        string            `json:"release_id"`
	SourceCommit     string            `json:"source_commit"`
	ProvenanceID     string            `json:"provenance_id"`
	Runtime          string            `json:"runtime"`
	Protocol         uint64            `json:"protocol"`
	GuestABI         uint64            `json:"guest_abi"`
	UISchema         uint64            `json:"ui_schema"`
	CapabilityHashes map[string]string `json:"capability_hashes"`
	CapabilityGrants CapabilityGrants  `json:"capability_grants"`
	StateMin         uint64            `json:"state_min"`
	StateMax         uint64            `json:"state_max"`
	PayloadSHA256    string            `json:"payload_sha256"`
	CompressedBytes  uint64            `json:"compressed_bytes"`
	ExpandedBytes    uint64            `json:"expanded_bytes"`
	Compression      string            `json:"compression"`
	AssetHashes      map[string]string `json:"asset_hashes"`
	SourceMapSHA256  string            `json:"source_map_sha256"`
	Limits           Limits            `json:"limits"`
	KeyID            string            `json:"key_id"`
	CreatedAtUnix    uint64            `json:"created_at_unix"`
}

type AssignmentV2 Assignment
type SignedManifestV2 struct {
	Manifest  ManifestV2 `json:"manifest"`
	Signature []byte     `json:"signature"`
}
type SignedAssignmentV2 struct {
	Assignment AssignmentV2 `json:"assignment"`
	Signature  []byte       `json:"signature"`
}

// profileFields reuses the frozen common-field validation only. No v2 object is
// signed, hashed, serialized, or granted authority through this temporary v1 view.
func (m ManifestV2) profileFields() Manifest {
	return Manifest{Schema: 1, Scope: m.Scope, ReleaseID: m.ReleaseID, SourceCommit: m.SourceCommit,
		ProvenanceID: m.ProvenanceID, Runtime: m.Runtime, Protocol: 1, GuestABI: m.GuestABI,
		UISchema: m.UISchema, CapabilityHashes: m.CapabilityHashes, StateMin: m.StateMin, StateMax: m.StateMax,
		PayloadSHA256: m.PayloadSHA256, CompressedBytes: m.CompressedBytes, ExpandedBytes: m.ExpandedBytes,
		Compression: m.Compression, AssetHashes: m.AssetHashes, SourceMapSHA256: m.SourceMapSHA256,
		Limits: m.Limits, KeyID: m.KeyID, CreatedAtUnix: m.CreatedAtUnix}
}

func (m ManifestV2) Validate() error {
	if m.Schema != 2 || m.Protocol != 2 {
		return fmt.Errorf("unsupported v2 manifest schema/protocol")
	}
	if e := m.profileFields().Validate(); e != nil {
		return e
	}
	return m.CapabilityGrants.Validate(m.CapabilityHashes)
}

func (a AssignmentV2) Validate() error {
	if a.Schema != 2 {
		return fmt.Errorf("unsupported v2 assignment schema")
	}
	common := Assignment(a)
	common.Schema = 1
	return common.Validate()
}

func (g CapabilityGrants) Validate(hashes map[string]string) error {
	if g.Schema != 1 || g.SchemaSHA256 != GrantSchemaSHA256 || g.Entries == nil || len(g.Entries) > 2 {
		return fmt.Errorf("invalid capability grant descriptor")
	}
	previous := ""
	for _, entry := range g.Entries {
		if entry.CapabilityID <= previous || !ValidID(entry.CapabilityID) {
			return fmt.Errorf("capability grants must be strictly ASCII sorted and unique")
		}
		previous = entry.CapabilityID
		http := entry.CapabilityID == HTTPGrantID
		permission, hash := "storage.appPrivate", StorageGrantSHA256
		if http {
			permission, hash = "network.https", HTTPGrantSHA256
		}
		if (!http && entry.CapabilityID != StorageGrantID) || entry.SchemaSHA256 != hash || hashes[entry.CapabilityID] != hash {
			return fmt.Errorf("unknown or unbound capability grant schema")
		}
		if !sortedASCII(entry.Permissions, 1) || !sortedASCII(entry.Origins, 32) || !sortedASCII(entry.Methods, 6) || !sortedASCII(entry.Namespaces, 32) {
			return fmt.Errorf("grant arrays must be explicit, bounded, strictly ASCII sorted and unique")
		}
		for _, value := range entry.Permissions {
			if value != permission {
				return fmt.Errorf("unsupported capability permission")
			}
		}
		if http {
			if len(entry.Namespaces) != 0 {
				return fmt.Errorf("HTTP grants cannot carry namespaces")
			}
			for _, value := range entry.Origins {
				if !ValidGrantOrigin(value) {
					return fmt.Errorf("noncanonical HTTP grant origin")
				}
			}
			for _, value := range entry.Methods {
				switch value {
				case "DELETE", "GET", "HEAD", "PATCH", "POST", "PUT":
				default:
					return fmt.Errorf("unsupported HTTP grant method")
				}
			}
		} else {
			if len(entry.Origins) != 0 || len(entry.Methods) != 0 {
				return fmt.Errorf("storage grants cannot carry HTTP authority")
			}
			for _, value := range entry.Namespaces {
				if !validNamespace(value) {
					return fmt.Errorf("invalid storage grant namespace")
				}
			}
		}
	}
	return nil
}

func sortedASCII(values []string, maximum int) bool {
	if values == nil || len(values) > maximum {
		return false
	}
	previous := ""
	for _, value := range values {
		if value <= previous || len(value) > 4096 {
			return false
		}
		for _, b := range []byte(value) {
			if b < 33 || b > 126 {
				return false
			}
		}
		previous = value
	}
	return true
}

func validNamespace(value string) bool {
	if len(value) < 1 || len(value) > 64 {
		return false
	}
	for _, b := range []byte(value) {
		if !(b >= 'A' && b <= 'Z' || b >= 'a' && b <= 'z' || b >= '0' && b <= '9' || b == '_' || b == '-') {
			return false
		}
	}
	return true
}

// ValidGrantOrigin matches the capability policy's exact ASCII origin grammar.
// It deliberately performs no URL normalization or suffix/wildcard matching.
func ValidGrantOrigin(value string) bool {
	if !strings.HasPrefix(value, "https://") || len(value) > 267 {
		return false
	}
	parts := strings.Split(value[8:], ":")
	if len(parts) < 1 || len(parts) > 2 || len(parts[0]) < 1 || len(parts[0]) > 253 {
		return false
	}
	for _, label := range strings.Split(parts[0], ".") {
		if len(label) < 1 || len(label) > 63 || label[0] == '-' || label[len(label)-1] == '-' {
			return false
		}
		for _, b := range []byte(label) {
			if !(b >= 'a' && b <= 'z' || b >= '0' && b <= '9' || b == '-') {
				return false
			}
		}
	}
	if len(parts) == 2 {
		port, e := strconv.ParseUint(parts[1], 10, 16)
		if e != nil || port == 0 || port == 443 || strconv.FormatUint(port, 10) != parts[1] {
			return false
		}
	}
	return true
}

func CompatibleV2(m ManifestV2, h Host) error {
	if e := m.Validate(); e != nil {
		return e
	}
	if h.Protocol != 2 {
		return fmt.Errorf("installed host did not negotiate update protocol 2")
	}
	h.Protocol = 1
	return Compatible(m.profileFields(), h)
}

func ManifestDigestV2(m ManifestV2) (string, error) {
	b, e := CanonicalCBOR(m)
	if e != nil {
		return "", e
	}
	return Hash(b), nil
}

func SignManifestV2(m ManifestV2, key ed25519.PrivateKey) (SignedManifestV2, error) {
	if e := m.Validate(); e != nil {
		return SignedManifestV2{}, e
	}
	if len(key) != ed25519.PrivateKeySize {
		return SignedManifestV2{}, fmt.Errorf("invalid private key")
	}
	b, e := CanonicalCBOR(m)
	if e != nil {
		return SignedManifestV2{}, e
	}
	return SignedManifestV2{m, ed25519.Sign(key, append([]byte(ArtifactDomainV2), b...))}, nil
}

func SignAssignmentV2(a AssignmentV2, key ed25519.PrivateKey) (SignedAssignmentV2, error) {
	if e := a.Validate(); e != nil {
		return SignedAssignmentV2{}, e
	}
	if len(key) != ed25519.PrivateKeySize {
		return SignedAssignmentV2{}, fmt.Errorf("invalid private key")
	}
	b, e := CanonicalCBOR(a)
	if e != nil {
		return SignedAssignmentV2{}, e
	}
	return SignedAssignmentV2{a, ed25519.Sign(key, append([]byte(AssignmentDomainV2), b...))}, nil
}

func VerifyManifestHeaderV2(s SignedManifestV2, roots []Root, h Host, now uint64) error {
	if e := CompatibleV2(s.Manifest, h); e != nil {
		return e
	}
	pub, e := authorize(roots, s.Manifest.KeyID, s.Manifest.Scope, true, now)
	if e != nil {
		return e
	}
	b, e := CanonicalCBOR(s.Manifest)
	if e != nil {
		return e
	}
	if !ed25519.Verify(pub, append([]byte(ArtifactDomainV2), b...), s.Signature) {
		return fmt.Errorf("v2 artifact signature invalid")
	}
	return nil
}

func VerifyManifestV2(s SignedManifestV2, payload []byte, roots []Root, h Host, now uint64) error {
	if e := VerifyManifestHeaderV2(s, roots, h, now); e != nil {
		return e
	}
	if uint64(len(payload)) != s.Manifest.CompressedBytes || Hash(payload) != s.Manifest.PayloadSHA256 {
		return fmt.Errorf("payload size or hash mismatch")
	}
	return nil
}

// Assignment verification rechecks the artifact's signing authority. It is header
// authorization only until VerifyManifestV2 has separately verified payload bytes.
func VerifyAssignmentHeaderV2(s SignedAssignmentV2, artifact SignedManifestV2, roots []Root, h Host, channel string, last, now uint64) error {
	if e := s.Assignment.Validate(); e != nil {
		return e
	}
	if e := VerifyManifestHeaderV2(artifact, roots, h, now); e != nil {
		return e
	}
	a, m := s.Assignment, artifact.Manifest
	digest, e := ManifestDigestV2(m)
	if e != nil {
		return e
	}
	if a.Scope != m.Scope || a.Runtime != m.Runtime || a.ReleaseID != m.ReleaseID || a.ArtifactSHA256 != digest || a.Channel != channel || !ValidID(channel) {
		return fmt.Errorf("v2 assignment binding mismatch")
	}
	if a.Sequence <= last {
		return fmt.Errorf("assignment replay")
	}
	pub, e := authorize(roots, a.KeyID, a.Scope, false, now)
	if e != nil {
		return e
	}
	b, e := CanonicalCBOR(a)
	if e != nil {
		return e
	}
	if !ed25519.Verify(pub, append([]byte(AssignmentDomainV2), b...), s.Signature) {
		return fmt.Errorf("v2 assignment signature invalid")
	}
	return nil
}

func VerifyAssignmentV2(s SignedAssignmentV2, artifact SignedManifestV2, roots []Root, h Host, channel, installation string, last, now uint64) error {
	if e := VerifyAssignmentHeaderV2(s, artifact, roots, h, channel, last, now); e != nil {
		return e
	}
	if !Eligible(Assignment(s.Assignment), installation) {
		return fmt.Errorf("installation outside cohort")
	}
	return nil
}

func DecodeSignedManifestV2(data []byte) (SignedManifestV2, error) {
	var value SignedManifestV2
	if len(data) > MaxV2DocumentBytes {
		return value, fmt.Errorf("v2 document exceeds byte limit")
	}
	e := DecodeJSON(data, &value)
	return value, e
}

func DecodeSignedAssignmentV2(data []byte) (SignedAssignmentV2, error) {
	var value SignedAssignmentV2
	if len(data) > MaxV2DocumentBytes {
		return value, fmt.Errorf("v2 document exceeds byte limit")
	}
	e := DecodeJSON(data, &value)
	return value, e
}

// Required zero-valued fields and empty arrays are not interchangeable with
// omitted fields. Only v2 structs add this requirement; v1 decoding stays frozen.
func exactV2Object(data []byte, fields ...string) (map[string]json.RawMessage, error) {
	if len(data) > MaxV2DocumentBytes {
		return nil, fmt.Errorf("v2 document exceeds byte limit")
	}
	var raw map[string]json.RawMessage
	if e := DecodeJSON(data, &raw); e != nil {
		return nil, e
	}
	if len(raw) != len(fields) {
		return nil, fmt.Errorf("missing or unknown v2 fields")
	}
	for _, field := range fields {
		if _, ok := raw[field]; !ok {
			return nil, fmt.Errorf("missing v2 field")
		}
	}
	return raw, nil
}

func (g *CapabilityGrant) UnmarshalJSON(data []byte) error {
	if _, e := exactV2Object(data, "capability_id", "schema_sha256", "permissions", "origins", "methods", "namespaces"); e != nil {
		return e
	}
	type plain CapabilityGrant
	return DecodeJSON(data, (*plain)(g))
}

func (g *CapabilityGrants) UnmarshalJSON(data []byte) error {
	if _, e := exactV2Object(data, "schema", "schema_sha256", "entries"); e != nil {
		return e
	}
	type plain CapabilityGrants
	return DecodeJSON(data, (*plain)(g))
}

func (m *ManifestV2) UnmarshalJSON(data []byte) error {
	raw, e := exactV2Object(data, "schema", "scope", "release_id", "source_commit", "provenance_id", "runtime", "protocol", "guest_abi", "ui_schema", "capability_hashes", "capability_grants", "state_min", "state_max", "payload_sha256", "compressed_bytes", "expanded_bytes", "compression", "asset_hashes", "source_map_sha256", "limits", "key_id", "created_at_unix")
	if e != nil {
		return e
	}
	if _, e = exactV2Object(raw["scope"], "organization", "project", "app", "environment", "platform"); e != nil {
		return e
	}
	if _, e = exactV2Object(raw["limits"], "memory_bytes", "fuel", "startup_milliseconds"); e != nil {
		return e
	}
	type plain ManifestV2
	return DecodeJSON(data, (*plain)(m))
}

func (a *AssignmentV2) UnmarshalJSON(data []byte) error {
	raw, e := exactV2Object(data, "schema", "scope", "channel", "cohort", "rollout_basis_points", "sequence", "release_id", "artifact_sha256", "runtime", "key_id", "created_at_unix")
	if e != nil {
		return e
	}
	if _, e = exactV2Object(raw["scope"], "organization", "project", "app", "environment", "platform"); e != nil {
		return e
	}
	type plain AssignmentV2
	return DecodeJSON(data, (*plain)(a))
}

func (s *SignedManifestV2) UnmarshalJSON(data []byte) error {
	raw, e := exactV2Object(data, "manifest", "signature")
	if e != nil {
		return e
	}
	if e = signatureEncodingV2(raw["signature"]); e != nil {
		return e
	}
	type plain SignedManifestV2
	return DecodeJSON(data, (*plain)(s))
}

func (s *SignedAssignmentV2) UnmarshalJSON(data []byte) error {
	raw, e := exactV2Object(data, "assignment", "signature")
	if e != nil {
		return e
	}
	if e = signatureEncodingV2(raw["signature"]); e != nil {
		return e
	}
	type plain SignedAssignmentV2
	return DecodeJSON(data, (*plain)(s))
}

func signatureEncodingV2(raw []byte) error {
	var text string
	if e := json.Unmarshal(raw, &text); e != nil || len(text) != 88 {
		return fmt.Errorf("v2 signature must be canonical base64 text")
	}
	decoded, e := base64.StdEncoding.Strict().DecodeString(text)
	if e != nil || len(decoded) != ed25519.SignatureSize || base64.StdEncoding.EncodeToString(decoded) != text {
		return fmt.Errorf("v2 signature must encode exactly 64 bytes in canonical padded base64")
	}
	return nil
}
