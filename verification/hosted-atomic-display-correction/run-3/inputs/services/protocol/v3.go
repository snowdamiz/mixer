package protocol

import (
	"crypto/ed25519"
	"fmt"
	"reflect"
)

const ArtifactDomainV3 = "mixer.artifact.v3\x00"
const AssignmentDomainV3 = "mixer.assignment.v3\x00"
const MaxV3DocumentBytes = 65536
const MaxV3PayloadBytes uint64 = 4 * 1024 * 1024
const MaxV3MemoryBytes uint64 = 4 * 1024 * 1024
const MaxV3Fuel uint64 = 1000000
const MaxV3StartupMilliseconds uint64 = 60000

// V3 has the same closed fields as V2 but an explicitly different negotiation
// tuple and signature domain. These mutable wire DTOs confer no execution
// authority. The installed native client must independently verify the exact
// payload, signed selection, identity and capability material before execution.
type ManifestV3 ManifestV2
type AssignmentV3 Assignment
type SignedManifestV3 struct {
	Manifest  ManifestV3 `json:"manifest"`
	Signature []byte     `json:"signature"`
}
type SignedAssignmentV3 struct {
	Assignment AssignmentV3 `json:"assignment"`
	Signature  []byte       `json:"signature"`
}

func capabilityHashesV3(hashes map[string]string) error {
	if hashes == nil || len(hashes) > 2 {
		return fmt.Errorf("v3 requires an explicit bounded capability map")
	}
	for id, digest := range hashes {
		switch id {
		case HTTPGrantID:
			if digest != HTTPGrantSHA256 {
				return fmt.Errorf("v3 HTTP schema mismatch")
			}
		case StorageGrantID:
			if digest != StorageGrantSHA256 {
				return fmt.Errorf("v3 storage schema mismatch")
			}
		default:
			return fmt.Errorf("unsupported v3 capability")
		}
	}
	return nil
}

func limitsV3(l Limits) error {
	if l.MemoryBytes == 0 || l.MemoryBytes > MaxV3MemoryBytes || l.Fuel == 0 || l.Fuel > MaxV3Fuel || l.StartupMilliseconds == 0 || l.StartupMilliseconds > MaxV3StartupMilliseconds {
		return fmt.Errorf("v3 resource limit outside installed execution profile")
	}
	return nil
}

func (m ManifestV3) Validate() error {
	if m.Schema != 3 || m.Protocol != 3 || m.GuestABI != 2 || m.UISchema != 1 {
		return fmt.Errorf("unsupported v3 schema, protocol, guest ABI or UI schema")
	}
	// Reuse only frozen common-field validation. This temporary view is never
	// signed, hashed, serialized or passed to a legacy verification function.
	common := ManifestV2(m).profileFields()
	common.GuestABI = 1
	if e := common.Validate(); e != nil {
		return e
	}
	if m.ExpandedBytes > MaxV3PayloadBytes {
		return fmt.Errorf("v3 payload exceeds execution profile")
	}
	if e := limitsV3(m.Limits); e != nil {
		return e
	}
	if e := capabilityHashesV3(m.CapabilityHashes); e != nil {
		return e
	}
	return m.CapabilityGrants.Validate(m.CapabilityHashes)
}

func (a AssignmentV3) Validate() error {
	if a.Schema != 3 {
		return fmt.Errorf("unsupported v3 assignment schema")
	}
	common := Assignment(a)
	common.Schema = 1
	return common.Validate()
}

// ValidateHostV3 validates a trusted installed configuration, not a downloaded
// identity or proof that a concrete native implementation matches its fingerprint.
func ValidateHostV3(h Host) error {
	if e := h.Scope.Validate(); e != nil {
		return e
	}
	if h.Protocol != 3 || h.GuestABI != 2 || h.UISchema != 1 || !ValidDigest(h.Runtime) || h.MaxPayloadBytes == 0 || h.MaxPayloadBytes > MaxV3PayloadBytes {
		return fmt.Errorf("unsupported v3 installed host")
	}
	if e := capabilityHashesV3(h.CapabilityHashes); e != nil {
		return e
	}
	return limitsV3(h.Limits)
}

func CompatibleV3(m ManifestV3, h Host) error {
	if e := m.Validate(); e != nil {
		return e
	}
	if e := ValidateHostV3(h); e != nil {
		return e
	}
	if m.Scope != h.Scope || m.Runtime != h.Runtime || !reflect.DeepEqual(m.CapabilityHashes, h.CapabilityHashes) {
		return fmt.Errorf("v3 host contract mismatch")
	}
	if h.StateVersion < m.StateMin || h.StateVersion > m.StateMax {
		return fmt.Errorf("state schema incompatible")
	}
	if m.ExpandedBytes > h.MaxPayloadBytes || m.Limits.MemoryBytes > h.Limits.MemoryBytes || m.Limits.Fuel > h.Limits.Fuel || m.Limits.StartupMilliseconds > h.Limits.StartupMilliseconds {
		return fmt.Errorf("host resource budget exceeded")
	}
	return nil
}

func validateRootsV3(roots []Root) error {
	if len(roots) == 0 || len(roots) > 128 {
		return fmt.Errorf("v3 trust root count outside bounds")
	}
	seen := make(map[string]bool, len(roots))
	for _, root := range roots {
		if !ValidID(root.KeyID) || seen[root.KeyID] || len(root.PublicKey) != ed25519.PublicKeySize || (!root.Artifact && !root.Assignment) || (root.NotAfterUnix != 0 && root.NotAfterUnix <= root.NotBeforeUnix) {
			return fmt.Errorf("invalid or ambiguous v3 trust root")
		}
		if e := root.Scope.Validate(); e != nil {
			return e
		}
		seen[root.KeyID] = true
	}
	return nil
}

func ManifestDigestV3(m ManifestV3) (string, error) {
	b, e := CanonicalCBOR(m)
	if e != nil {
		return "", e
	}
	return Hash(b), nil
}

func SignManifestV3(m ManifestV3, key ed25519.PrivateKey) (SignedManifestV3, error) {
	if e := m.Validate(); e != nil {
		return SignedManifestV3{}, e
	}
	if len(key) != ed25519.PrivateKeySize {
		return SignedManifestV3{}, fmt.Errorf("invalid private key")
	}
	b, e := CanonicalCBOR(m)
	if e != nil {
		return SignedManifestV3{}, e
	}
	return SignedManifestV3{m, ed25519.Sign(key, append([]byte(ArtifactDomainV3), b...))}, nil
}

func SignAssignmentV3(a AssignmentV3, key ed25519.PrivateKey) (SignedAssignmentV3, error) {
	if e := a.Validate(); e != nil {
		return SignedAssignmentV3{}, e
	}
	if len(key) != ed25519.PrivateKeySize {
		return SignedAssignmentV3{}, fmt.Errorf("invalid private key")
	}
	b, e := CanonicalCBOR(a)
	if e != nil {
		return SignedAssignmentV3{}, e
	}
	return SignedAssignmentV3{a, ed25519.Sign(key, append([]byte(AssignmentDomainV3), b...))}, nil
}

func VerifyManifestHeaderV3(s SignedManifestV3, roots []Root, h Host, now uint64) error {
	if e := validateRootsV3(roots); e != nil {
		return e
	}
	if e := CompatibleV3(s.Manifest, h); e != nil {
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
	if !ed25519.Verify(pub, append([]byte(ArtifactDomainV3), b...), s.Signature) {
		return fmt.Errorf("v3 artifact signature invalid")
	}
	return nil
}

func VerifyManifestV3(s SignedManifestV3, payload []byte, roots []Root, h Host, now uint64) error {
	if e := VerifyManifestHeaderV3(s, roots, h, now); e != nil {
		return e
	}
	if uint64(len(payload)) != s.Manifest.CompressedBytes || Hash(payload) != s.Manifest.PayloadSHA256 {
		return fmt.Errorf("payload size or hash mismatch")
	}
	return nil
}

// Assignment verification rechecks the artifact's signing authority. It is header
// authorization only until VerifyManifestV3 has separately verified payload bytes.
func VerifyAssignmentHeaderV3(s SignedAssignmentV3, artifact SignedManifestV3, roots []Root, h Host, channel string, last, now uint64) error {
	if e := s.Assignment.Validate(); e != nil {
		return e
	}
	if e := VerifyManifestHeaderV3(artifact, roots, h, now); e != nil {
		return e
	}
	a, m := s.Assignment, artifact.Manifest
	digest, e := ManifestDigestV3(m)
	if e != nil {
		return e
	}
	if a.Scope != m.Scope || a.Runtime != m.Runtime || a.ReleaseID != m.ReleaseID || a.ArtifactSHA256 != digest || a.Channel != channel || !ValidID(channel) {
		return fmt.Errorf("v3 assignment binding mismatch")
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
	if !ed25519.Verify(pub, append([]byte(AssignmentDomainV3), b...), s.Signature) {
		return fmt.Errorf("v3 assignment signature invalid")
	}
	return nil
}

func VerifyAssignmentV3(s SignedAssignmentV3, artifact SignedManifestV3, roots []Root, h Host, channel, installation string, last, now uint64) error {
	if e := VerifyAssignmentHeaderV3(s, artifact, roots, h, channel, last, now); e != nil {
		return e
	}
	if !Eligible(Assignment(s.Assignment), installation) {
		return fmt.Errorf("installation outside cohort")
	}
	return nil
}

func DecodeSignedManifestV3(data []byte) (SignedManifestV3, error) {
	var value SignedManifestV3
	if len(data) > MaxV3DocumentBytes {
		return value, fmt.Errorf("v3 document exceeds byte limit")
	}
	e := DecodeJSON(data, &value)
	return value, e
}

func DecodeSignedAssignmentV3(data []byte) (SignedAssignmentV3, error) {
	var value SignedAssignmentV3
	if len(data) > MaxV3DocumentBytes {
		return value, fmt.Errorf("v3 document exceeds byte limit")
	}
	e := DecodeJSON(data, &value)
	return value, e
}

// Exact V2 wire shape is shared, never V2 semantic or signature authority.
// Decoding alone does not validate negotiation or grant execution authority.
func (m *ManifestV3) UnmarshalJSON(data []byte) error {
	var value ManifestV2
	if e := value.UnmarshalJSON(data); e != nil {
		return e
	}
	*m = ManifestV3(value)
	return nil
}
func (a *AssignmentV3) UnmarshalJSON(data []byte) error {
	var value AssignmentV2
	if e := value.UnmarshalJSON(data); e != nil {
		return e
	}
	*a = AssignmentV3(value)
	return nil
}
func (s *SignedManifestV3) UnmarshalJSON(data []byte) error {
	var value SignedManifestV2
	if e := value.UnmarshalJSON(data); e != nil {
		return e
	}
	*s = SignedManifestV3{Manifest: ManifestV3(value.Manifest), Signature: value.Signature}
	return nil
}
func (s *SignedAssignmentV3) UnmarshalJSON(data []byte) error {
	var value SignedAssignmentV2
	if e := value.UnmarshalJSON(data); e != nil {
		return e
	}
	*s = SignedAssignmentV3{Assignment: AssignmentV3(value.Assignment), Signature: value.Signature}
	return nil
}
